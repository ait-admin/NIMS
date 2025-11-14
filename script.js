(function(){
	const form = document.getElementById('kioskForm');
	const input = document.getElementById('crInput');
	const statusEl = document.getElementById('status');
    const submitBtn = document.getElementById('submitBtn');

    // Play TTS in background and resolve when playback finishes (or timeout)
    let ttsAudioEl;
    function playTTS(text, maxMs) {
        const msg = String(text || '').trim();
        if (!msg) return Promise.resolve();
        var maxWaitMs = typeof maxMs === 'number' ? maxMs : 6000;
        try {
            return fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: msg })
            }).then(function(res){
                if (!res.ok) throw new Error('tts_failed');
                return res.blob();
            }).then(function(blob){
                return new Promise(function(resolve){
                    try {
                        if (!ttsAudioEl) {
                            ttsAudioEl = document.createElement('audio');
                            ttsAudioEl.setAttribute('playsinline','');
                            ttsAudioEl.style.display = 'none';
                            document.body.appendChild(ttsAudioEl);
                        }
                        const url = URL.createObjectURL(blob);
                        ttsAudioEl.src = url;

                        var resolved = false;
                        var cleanup = function(){
                            if (resolved) return;
                            resolved = true;
                            try { ttsAudioEl.removeEventListener('ended', onEnded); } catch(e) {}
                            try { URL.revokeObjectURL(url); } catch(e) {}
                            resolve();
                        };
                        var onEnded = function(){ cleanup(); };
                        ttsAudioEl.addEventListener('ended', onEnded, { once: true });
                        // Fallback timeout in case 'ended' never fires
                        setTimeout(cleanup, maxWaitMs);

                        var playPromise = ttsAudioEl.play();
                        if (playPromise && typeof playPromise.catch === 'function') {
                            playPromise.catch(function(){ cleanup(); });
                        }
                    } catch(e) {
                        resolve();
                    }
                });
            }).catch(function(){ return Promise.resolve(); });
        } catch (e) {
            return Promise.resolve();
        }
    }

	function setStatus(message, type) {
		statusEl.textContent = message || '';
		statusEl.classList.remove('error', 'success');
		if (type) statusEl.classList.add(type);
	}

	function ensureFocus() {
		if (document.activeElement !== input) {
			input.focus();
		}
	}


	// Keep input focused periodically (no idle voice prompt)
	let lastInputAt = Date.now();
	setInterval(ensureFocus, 3000);

    if (form && input) {
        let submitTimer = null;
        let isSubmitting = false;
        const MIN_LEN = 5; // minimum characters to consider a valid CR scan
        // On-screen keypad
        document.querySelectorAll('.keypad .key').forEach(function(btn){
            btn.addEventListener('click', function(){
                const action = btn.getAttribute('data-action');
                if (action === 'clear') {
                    input.value = '';
                    setStatus('', '');
                    return;
                }
                if (action === 'backspace') {
                    input.value = (input.value || '').slice(0, -1);
                    return;
                }
                const digit = btn.textContent.trim();
                if (/^\d$/.test(digit)) {
                    input.value = (input.value || '') + digit;
                }
                ensureFocus();
            });
        });

        if (submitBtn) {
            submitBtn.addEventListener('click', function(){
                form.requestSubmit();
            });
        }

        // Debounced auto-submit on input (scanner typing)
        input.addEventListener('input', function(){
            lastInputAt = Date.now();
            if (submitTimer) clearTimeout(submitTimer);
            submitTimer = setTimeout(function(){
                const value = (input.value || '').trim();
                if (value.length >= MIN_LEN && !isSubmitting) {
                    form.requestSubmit();
                }
            }, 200);
        });

        // Submit on Enter; scanners typically send Enter at the end
		form.addEventListener('submit', function(e){
			e.preventDefault();
			const cr = (input.value || '').trim();
            if (!cr || isSubmitting) return;
            isSubmitting = true;
			// Telugu UI status
			setStatus('మీ అపాయింట్‌మెంట్ బుక్ అవుతోంది...', '');
			lastInputAt = Date.now();

			const formData = new URLSearchParams();
			formData.set('cr_number', cr);

			fetch('/book_appointment', {
				method: 'POST',
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: formData.toString()
			}).then(async function(res){
				if (!res.ok) {
					const err = await res.json().catch(function(){ return { message: 'Unknown error' }; });
					throw new Error(err.message || 'Invalid CR Number. Please contact helpdesk.');
				}
				return res.json();
            }).then(function(data){
				setStatus('అపాయింట్‌మెంట్ విజయవంతంగా బుక్ అయింది.', 'success');
				const message = 'మీ అపాయింట్‌మెంట్ ' + (data.doctor || 'డాక్టర్') + ' వద్ద ' + (data.appointment_time || 'నిర్దేశిత సమయం') + 'కి బుక్ అయింది.';
				playTTS(message).catch(function(){});
				window.location.href = '/print_slip/' + encodeURIComponent(data.appointment_id);
            }).catch(function(err){
				// Ensure Telugu message; otherwise replace
                let msg = err.message || '';
                // Map specific backend codes/messages to Telugu
                if (err && err.message && typeof err.message === 'string' && err.message.indexOf('వాలిడిటీ సమయం పూర్తైంది') >= 0) {
                    msg = 'మీ 14 రోజుల వాలిడిటీ సమయం పూర్తైంది. దయచేసి కొత్త రిజిస్ట్రేషన్ చేయించుకోండి.';
                } else if (!/[\u0C00-\u0C7F]/.test(msg)) {
                    msg = 'తప్పు CR నంబర్. దయచేసి హెల్ప్ డెస్క్‌ను సంప్రదించండి.';
                }
				setStatus(msg, 'error');
                // Speak, then redirect only AFTER TTS completes (with safe timeout)
                playTTS(msg, 8000).then(function(){
                    window.location.href = '/';
                });
            }).finally(function(){
                isSubmitting = false;
			});
		});

		// Some scanners may send Enter key; ensure form submission
		input.addEventListener('keydown', function(ev){
			if (ev.key === 'Enter') {
				form.requestSubmit();
			}
		});

		// Force autofocus after load
		window.addEventListener('load', ensureFocus);
		window.addEventListener('focus', ensureFocus);
	}
})();



