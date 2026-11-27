/*
 * Audio recorder for practice clips (Alpine.js).
 *
 * recorderMixin(opts) holds the recording state and is spread into:
 *   - practiceClipManager(opts): record/upload clips on Log/Edit practice
 *   - practiceReplyForm(opts):   text and/or audio reply in a clip thread
 *
 * Flow: mic permission -> live level meter -> record (auto-stop at the
 * limit) -> listen back -> keep or redo. If MediaRecorder or the mic isn't
 * available, the user can pick a file instead (on phones this can open the
 * voice recorder).
 *
 * Kept free of getters so the mixin can be spread with {...}.
 */
(function () {
    'use strict';

    var MIME_TYPES = [
        'audio/webm;codecs=opus',
        'audio/mp4',
        'audio/webm',
        'audio/ogg;codecs=opus',
    ];

    function pickMimeType() {
        if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return '';
        for (var i = 0; i < MIME_TYPES.length; i++) {
            if (MediaRecorder.isTypeSupported(MIME_TYPES[i])) return MIME_TYPES[i];
        }
        return '';
    }

    function extensionFor(type) {
        if (!type) return '.webm';
        if (type.indexOf('mp4') !== -1 || type.indexOf('aac') !== -1) return '.m4a';
        if (type.indexOf('ogg') !== -1) return '.ogg';
        if (type.indexOf('mpeg') !== -1) return '.mp3';
        if (type.indexOf('wav') !== -1) return '.wav';
        return '.webm';
    }

    function formatTime(seconds) {
        seconds = Math.max(0, Math.floor(seconds || 0));
        var m = Math.floor(seconds / 60);
        var s = seconds % 60;
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    function micHelp() {
        var ua = navigator.userAgent || '';
        if (/iPhone|iPad|iPod/.test(ua)) {
            return 'To allow the microphone, open Settings > Safari > Microphone (or tap "aA" in the address bar > Website Settings), choose Allow, then reload this page.';
        }
        if (/Android/.test(ua)) {
            return 'To allow the microphone, tap the icon to the left of the address, choose Permissions > Microphone > Allow, then reload this page.';
        }
        if (/Firefox/.test(ua)) {
            return 'To allow the microphone, click the microphone icon in the address bar, remove the block, then reload this page.';
        }
        if (/Safari/.test(ua) && !/Chrome/.test(ua)) {
            return 'To allow the microphone, open Safari > Settings for This Website > Microphone > Allow, then reload this page.';
        }
        return 'To allow the microphone, click the icon to the left of the address bar, set Microphone to Allow, then reload this page.';
    }

    function csrfToken() {
        var input = document.querySelector('input[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    /* POST FormData with upload progress. Resolves with parsed JSON. */
    function postForm(url, formData, onProgress) {
        return new Promise(function (resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            xhr.setRequestHeader('X-CSRFToken', csrfToken());
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            if (xhr.upload && onProgress) {
                xhr.upload.onprogress = function (e) {
                    if (e.lengthComputable) onProgress(Math.round(100 * e.loaded / e.total));
                };
            }
            xhr.onload = function () {
                var data = null;
                try { data = JSON.parse(xhr.responseText); } catch (e) { /* not JSON */ }
                if (xhr.status >= 200 && xhr.status < 300 && data && data.ok) {
                    resolve(data);
                } else if (xhr.status === 413 && !data) {
                    reject(new Error('The recording is too large to upload.'));
                } else {
                    reject(new Error((data && data.error) || 'Upload failed. Please try again.'));
                }
            };
            xhr.onerror = function () { reject(new Error('Network error. Check your connection and try again.')); };
            xhr.send(formData);
        });
    }

    window.recorderMixin = function (opts) {
        return {
            maxSeconds: opts.maxSeconds || 90,
            maxUploadMb: opts.maxUploadMb || 10,
            recState: 'idle',   // idle | requesting | recording | recorded | denied
            supported: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia &&
                           typeof MediaRecorder !== 'undefined'),
            elapsed: 0,
            level: 0,
            blob: null,
            blobName: '',
            blobUrl: '',
            recError: '',
            micHelpText: '',
            statusText: '',
            _stream: null,
            _recorder: null,
            _chunks: [],
            _timer: null,
            _startedAt: 0,
            _audioCtx: null,
            _raf: null,

            formatTime: formatTime,

            async startRecording() {
                this.recError = '';
                this.discardRecording();
                this.recState = 'requesting';
                this.statusText = 'Waiting for microphone permission';
                try {
                    this._stream = await navigator.mediaDevices.getUserMedia({
                        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
                    });
                } catch (err) {
                    this.recState = 'denied';
                    this.micHelpText = micHelp();
                    this.statusText = 'Microphone not available';
                    return;
                }
                var mimeType = pickMimeType();
                try {
                    this._recorder = mimeType ? new MediaRecorder(this._stream, { mimeType: mimeType })
                                              : new MediaRecorder(this._stream);
                } catch (err) {
                    this._releaseMic();
                    this.recState = 'idle';
                    this.supported = false;
                    this.recError = "Recording isn't supported in this browser. Please choose a file instead.";
                    return;
                }
                var self = this;
                this._chunks = [];
                this._recorder.ondataavailable = function (e) { if (e.data && e.data.size) self._chunks.push(e.data); };
                this._recorder.onstop = function () { self._finishRecording(); };
                this._recorder.start(1000);
                this._startedAt = Date.now();
                this.elapsed = 0;
                this.recState = 'recording';
                this.statusText = 'Recording';
                this._timer = setInterval(function () {
                    self.elapsed = (Date.now() - self._startedAt) / 1000;
                    if (self.elapsed >= self.maxSeconds) self.stopRecording();
                }, 200);
                this._startMeter();
            },

            stopRecording() {
                if (this._recorder && this._recorder.state !== 'inactive') this._recorder.stop();
                clearInterval(this._timer);
                this._timer = null;
            },

            _finishRecording() {
                var type = (this._recorder && this._recorder.mimeType) || 'audio/webm';
                this.blob = new Blob(this._chunks, { type: type });
                this.blobName = 'recording' + extensionFor(type);
                this.blobUrl = URL.createObjectURL(this.blob);
                this._releaseMic();
                this.recState = 'recorded';
                this.statusText = 'Recording finished, ' + formatTime(this.elapsed) + ' long. Listen back, then keep it or record again.';
            },

            _startMeter() {
                var Ctx = window.AudioContext || window.webkitAudioContext;
                if (!Ctx) return;
                try {
                    this._audioCtx = new Ctx();
                    var source = this._audioCtx.createMediaStreamSource(this._stream);
                    var analyser = this._audioCtx.createAnalyser();
                    analyser.fftSize = 1024;
                    source.connect(analyser);
                    var data = new Uint8Array(analyser.fftSize);
                    var self = this;
                    var tick = function () {
                        analyser.getByteTimeDomainData(data);
                        var sum = 0;
                        for (var i = 0; i < data.length; i++) {
                            var v = (data[i] - 128) / 128;
                            sum += v * v;
                        }
                        self.level = Math.min(1, Math.sqrt(sum / data.length) * 3);
                        if (self.recState === 'recording') self._raf = requestAnimationFrame(tick);
                    };
                    tick();
                } catch (e) { /* the meter is optional */ }
            },

            _releaseMic() {
                if (this._raf) cancelAnimationFrame(this._raf);
                this._raf = null;
                this.level = 0;
                if (this._audioCtx) { try { this._audioCtx.close(); } catch (e) { /* ignore */ } }
                this._audioCtx = null;
                if (this._stream) this._stream.getTracks().forEach(function (t) { t.stop(); });
                this._stream = null;
            },

            discardRecording() {
                if (this.blobUrl) URL.revokeObjectURL(this.blobUrl);
                this.blob = null;
                this.blobName = '';
                this.blobUrl = '';
                this.elapsed = 0;
                if (this.recState === 'recorded') this.recState = 'idle';
            },

            redoRecording() {
                this.discardRecording();
                this.recState = 'idle';
                this.statusText = 'Recording discarded';
            },

            chooseFile(event) {
                var file = event.target.files && event.target.files[0];
                event.target.value = '';
                if (!file) return;
                this.recError = '';
                if (file.size > this.maxUploadMb * 1024 * 1024) {
                    this.recError = 'That file is larger than ' + this.maxUploadMb + ' MB. Please choose a shorter recording.';
                    return;
                }
                this.discardRecording();
                this.blob = file;
                this.blobName = file.name;
                this.blobUrl = URL.createObjectURL(file);
                this.elapsed = 0;
                this.recState = 'recorded';
                this.statusText = 'File chosen: ' + file.name + '. Listen back, then keep it or choose another.';
            },

            onPreviewLoaded(event) {
                // For chosen files, show the real length (and warn if too long)
                var d = event.target.duration;
                if (isFinite(d) && d > 0) {
                    this.elapsed = d;
                    if (d > this.maxSeconds + 2) {
                        this.recError = 'This recording is ' + formatTime(d) + ' long. The limit is ' +
                            formatTime(this.maxSeconds) + ', so it will be rejected.';
                    }
                }
            },

            levelStyle() {
                return 'width:' + Math.round(this.level * 100) + '%';
            },
        };
    };

    /* Log / Edit practice: record or choose clips and attach them. */
    window.practiceClipManager = function (opts) {
        var base = window.recorderMixin(opts);
        return Object.assign(base, {
            uploadUrl: opts.uploadUrl,
            statusUrlTemplate: opts.statusUrlTemplate,   // contains 00000000-0000-0000-0000-000000000000
            maxClips: opts.maxClips || 3,
            clips: opts.initialClips || [],
            adding: false,
            kind: 'piece',
            title: '',
            note: '',
            uploading: false,
            progress: 0,
            uploadError: '',

            init() {
                var self = this;
                this.clips.forEach(function (c) { if (c.status === 'processing') self.pollStatus(c); });
            },

            canAddMore() {
                return this.clips.length < this.maxClips;
            },

            startAdding() {
                this.adding = true;
                this.uploadError = '';
                this.recError = '';
            },

            cancelAdding() {
                this.stopRecording();
                this._releaseMic();
                this.discardRecording();
                this.recState = 'idle';
                this.adding = false;
                this.title = '';
                this.note = '';
                this.kind = 'piece';
            },

            async attachClip() {
                this.uploadError = '';
                if (!this.blob) { this.uploadError = 'Please record or choose a clip first.'; return; }
                if (!this.title.trim()) { this.uploadError = 'Please give the clip a title.'; return; }
                var fd = new FormData();
                fd.append('audio', this.blob, this.blobName || 'recording.webm');
                fd.append('kind', this.kind);
                fd.append('title', this.title.trim());
                fd.append('note', this.note.trim());
                this.uploading = true;
                this.progress = 0;
                this.statusText = 'Uploading clip';
                var self = this;
                try {
                    var clip = await postForm(this.uploadUrl, fd, function (p) { self.progress = p; });
                    this.clips.push(clip);
                    this.statusText = 'Clip "' + clip.title + '" attached';
                    this.cancelAdding();
                    if (clip.status === 'processing') this.pollStatus(clip);
                } catch (err) {
                    this.uploadError = err.message;
                    this.statusText = err.message;
                } finally {
                    this.uploading = false;
                }
            },

            pollStatus(clip, attempt) {
                attempt = attempt || 0;
                if (attempt > 60) return;   // about 3 minutes
                var self = this;
                var url = this.statusUrlTemplate.replace('00000000-0000-0000-0000-000000000000', clip.id);
                setTimeout(function () {
                    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
                        .then(function (r) { return r.ok ? r.json() : null; })
                        .then(function (data) {
                            if (!data) return;
                            var i = self.clips.findIndex(function (c) { return c.id === data.id; });
                            if (i === -1) return;
                            self.clips.splice(i, 1, data);
                            if (data.status === 'processing') self.pollStatus(data, attempt + 1);
                        })
                        .catch(function () { self.pollStatus(clip, attempt + 1); });
                }, 3000);
            },

            async removeClip(clip) {
                if (!confirm('Remove the clip "' + clip.title + '"? This deletes the recording.')) return;
                try {
                    await postForm(clip.delete_url, new FormData());
                    this.clips = this.clips.filter(function (c) { return c.id !== clip.id; });
                    this.statusText = 'Clip removed';
                } catch (err) {
                    this.uploadError = err.message;
                }
            },
        });
    };

    /* Reply in a clip thread: text and/or a recording. */
    window.practiceReplyForm = function (opts) {
        var base = window.recorderMixin(opts);
        return Object.assign(base, {
            url: opts.url,
            text: '',
            showRecorder: false,
            sending: false,
            progress: 0,
            sendError: '',

            async send() {
                this.sendError = '';
                if (!this.text.trim() && !this.blob) {
                    this.sendError = 'Please write a reply or record one.';
                    return;
                }
                if (this.recState === 'recording') this.stopRecording();
                var fd = new FormData();
                fd.append('text', this.text.trim());
                if (this.blob) fd.append('audio', this.blob, this.blobName || 'recording.webm');
                this.sending = true;
                this.progress = 0;
                this.statusText = 'Sending';
                var self = this;
                try {
                    await postForm(this.url, fd, function (p) { self.progress = p; });
                    this.statusText = 'Sent';
                    window.location.reload();
                } catch (err) {
                    this.sendError = err.message;
                    this.statusText = err.message;
                    this.sending = false;
                }
            },
        });
    };
})();
