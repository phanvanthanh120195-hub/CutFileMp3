let state = {
    filePath: null,
    duration: 0,
    segments: [],
    outputFolder: null,
    playingIdx: null
};

// DOM Elements
const els = {
    inputFile: document.getElementById('input-file-path'),
    browseFileBtn: document.getElementById('browse-file-btn'),
    fileInfo: document.getElementById('file-info'),
    fileDuration: document.getElementById('file-duration'),
    segmentLength: document.getElementById('segment-length'),
    keepLockedCb: document.getElementById('keep-locked-cb'),
    generateBtn: document.getElementById('generate-segments-btn'),
    segmentsList: document.getElementById('segments-list'),
    addSegmentBtn: document.getElementById('add-segment-btn'),
    clearSegmentsBtn: document.getElementById('clear-segments-btn'),
    outputFolder: document.getElementById('output-folder-path'),
    browseFolderBtn: document.getElementById('browse-folder-btn'),
    exportBtn: document.getElementById('export-btn'),
    exportZipBtn: document.getElementById('export-zip-btn'),
    exportStatus: document.getElementById('export-status')
};

// Utils
function formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function parseTime(timeStr) {
    const parts = timeStr.split(':').map(Number);
    if (parts.length !== 3) return 0;
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
}

function getSegmentLength() {
    const val = els.segmentLength.value.trim();
    if (val.includes(':')) {
        return parseTime(val);
    }
    return parseInt(val) || 0;
}

// Event Listeners
els.browseFileBtn.addEventListener('click', async () => {
    const res = await fetch('/api/browse-file');
    const data = await res.json();
    if (data.path) {
        state.filePath = data.path;
        els.inputFile.value = state.filePath;
        loadFileInfo();
    }
});

els.browseFolderBtn.addEventListener('click', async () => {
    const res = await fetch('/api/browse-folder');
    const data = await res.json();
    if (data.path) {
        state.outputFolder = data.path;
        els.outputFolder.value = state.outputFolder;
        checkExportReady();
    }
});

els.generateBtn.addEventListener('click', () => generateSegments(true));
els.addSegmentBtn.addEventListener('click', addSegment);
els.clearSegmentsBtn.addEventListener('click', () => {
    state.segments = [];
    renderSegments();
});
els.exportBtn.addEventListener('click', () => exportSegments(false));
els.exportZipBtn.addEventListener('click', () => exportSegments(true));

async function loadFileInfo() {
    try {
        const res = await fetch('/api/file-info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: state.filePath })
        });
        const data = await res.json();
        if (data.duration) {
            state.duration = data.duration;
            els.fileDuration.textContent = formatTime(state.duration);
            els.fileInfo.classList.remove('hidden');
            els.generateBtn.disabled = false;

            // Reset segments when a new file is selected
            state.segments = [];
            renderSegments();
        }
    } catch (err) {
        console.error(err);
        alert('Error loading file info');
    }
}

function generateSegments(isReset) {
    const segLen = getSegmentLength();
    if (!segLen || segLen <= 0) {
        alert("Please enter a valid segment length (HH:MM:SS or seconds)");
        return;
    }

    const keepLocked = els.keepLockedCb.checked;
    let newSegments = [];
    let currentTime = 0;
    let segmentIdx = 1;

    // Identify anchors if keeping locked
    let anchors = [];
    if (keepLocked && state.segments.length > 0) {
        anchors = state.segments.filter(s => s.locked).sort((a, b) => a.start - b.start);
    }

    // Helper to fill gap
    const fillGap = (start, end) => {
        let t = start;
        while (t < end - 0.1) { // Tolerance
            let nextEnd = Math.min(t + segLen, end);
            newSegments.push({
                id: Date.now() + Math.random(),
                start: t,
                end: nextEnd,
                locked: false,
                outputName: `segment_${segmentIdx.toString().padStart(2, '0')}`
            });
            t = nextEnd;
            segmentIdx++;
        }
    };

    if (anchors.length === 0) {
        fillGap(0, state.duration);
    } else {
        // Fill before first anchor
        if (anchors[0].start > 0) {
            fillGap(0, anchors[0].start);
        }

        // Fill between anchors
        for (let i = 0; i < anchors.length; i++) {
            const anchor = anchors[i];
            // Add anchor itself
            newSegments.push(anchor);
            segmentIdx++; // Increment for naming consistency if we want, or keep anchor name?
            // Let's keep anchor name but maybe update index if we were strictly renaming. 
            // For now, we trust anchor has a name.

            const nextStart = (i < anchors.length - 1) ? anchors[i + 1].start : state.duration;
            if (anchor.end < nextStart) {
                fillGap(anchor.end, nextStart);
            }
        }
    }

    // Sort by start time just in case
    newSegments.sort((a, b) => a.start - b.start);

    // Renumber output names if generated? 
    // User might want to keep names of locked segments.
    // Let's just re-index the auto-generated ones or all?
    // Requirement says: "Reset Auto".
    // Let's re-generate names for non-locked segments to be consistent.
    let idx = 1;
    newSegments.forEach(seg => {
        if (!seg.locked) {
            seg.outputName = `segment_${idx.toString().padStart(2, '0')}`;
        }
        idx++;
    });

    state.segments = newSegments;
    renderSegments();
}

function addSegment() {
    const lastSeg = state.segments[state.segments.length - 1];
    const start = lastSeg ? lastSeg.end : 0;
    const end = Math.min(start + 60, state.duration);

    state.segments.push({
        id: Date.now() + Math.random(),
        start: start,
        end: end,
        locked: false,
        outputName: `segment_auto` // Temp, will be renumbered
    });
    renumberSegments();
    renderSegments();
}

function renderSegments() {
    els.segmentsList.innerHTML = '';
    if (state.segments.length === 0) {
        els.segmentsList.innerHTML = '<div class="empty-state">No segments generated yet.</div>';
        checkExportReady();
        return;
    }

    state.segments.forEach((seg, index) => {
        const row = document.createElement('div');
        row.className = `segment-row ${seg.locked ? 'locked' : ''} ${state.playingIdx === index ? 'playing' : ''}`;
        row.dataset.idx = index;

        // Shift input only for index > 0
        const shiftInput = index > 0 ? `<input type="number" class="shift-input" placeholder="+/- min" data-idx="${index}">` : '';
        const shiftSecInput = index > 0 ? `<input type="number" class="shift-sec-input" placeholder="+/- s" data-idx="${index}">` : '';

        row.innerHTML = `
            <div class="idx">${index + 1}</div>
            <input type="text" class="time-input start" value="${formatTime(seg.start)}" data-idx="${index}" data-field="start">
            <div style="text-align: center;">${shiftInput}</div>
            <div style="text-align: center;">${shiftSecInput}</div>
            <input type="text" class="time-input end" value="${formatTime(seg.end)}" data-idx="${index}" data-field="end">
            <div style="text-align: center;">
                <input type="checkbox" ${seg.locked ? 'checked' : ''} data-idx="${index}" class="lock-cb">
            </div>
            <div class="col-duration">
                ${formatTime(seg.end - seg.start)}
            </div>
            <input type="text" value="${seg.outputName}" data-idx="${index}" data-field="outputName" class="name-input">
            <button class="del-btn" data-idx="${index}">×</button>
        `;
        els.segmentsList.appendChild(row);
    });

    attachListeners();
    checkExportReady();
}

function attachListeners() {
    document.querySelectorAll('.time-input').forEach(inp => {
        inp.addEventListener('change', handleTimeChange);
    });
    document.querySelectorAll('.shift-input').forEach(inp => {
        inp.addEventListener('change', handleShiftChange);
    });
    document.querySelectorAll('.lock-cb').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            state.segments[idx].locked = e.target.checked;
            renderSegments(); // Re-render to show visual lock state
        });
    });
    document.querySelectorAll('.name-input').forEach(inp => {
        inp.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            state.segments[idx].outputName = e.target.value;
        });
    });
    document.querySelectorAll('.shift-sec-input').forEach(el => {
        el.addEventListener('change', (e) => {
            handleShiftSecondsChange(e);
        });
    });
    document.querySelectorAll('.del-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            state.segments.splice(idx, 1);
            // If we delete, we might create a gap. 
            // For now, just render. User can manually adjust or regenerate.
            renumberSegments();
            renderSegments();
        });
    });
}

function handleShiftChange(e) {
    const idx = parseInt(e.target.dataset.idx);
    const valMinutes = parseFloat(e.target.value);

    if (isNaN(valMinutes) || valMinutes === 0) return;

    const valSeconds = valMinutes * 60; // Convert minutes to seconds
    const seg = state.segments[idx];
    const oldStart = seg.start;
    const newStart = oldStart + valSeconds;

    // Find limit (Next Locked Segment or Total Duration)
    let limitTime = state.duration;
    const nextAnchorIdx = state.segments.findIndex((s, i) => i > idx && s.locked);
    if (nextAnchorIdx !== -1) {
        limitTime = state.segments[nextAnchorIdx].start;
    }

    // Validate New Start
    if (newStart >= limitTime) {
        alert(`Cannot shift start beyond limit (${formatTime(limitTime)}).`);
        e.target.value = ""; // Clear input
        return;
    }

    if (newStart < 0) {
        alert("Cannot shift start before 00:00:00.");
        e.target.value = "";
        return;
    }

    // Update Start
    seg.start = newStart;

    // Update End to preserve duration
    const duration = seg.end - oldStart;
    seg.end = seg.start + duration;

    // Update previous segment end if not locked
    if (idx > 0) {
        const prev = state.segments[idx - 1];
        if (!prev.locked) {
            prev.end = seg.start;
        } else if (seg.start < prev.end) {
            // Conflict with locked previous
            alert("Cannot shift start before previous locked segment end.");
            // Revert
            seg.start = oldStart;
            seg.end = oldStart + duration;
            e.target.value = "";
            renderSegments();
            return;
        }
    }

    // Cascade from this segment
    cascadeFrom(idx);
    renderSegments();
}

function handleShiftSecondsChange(e) {
    const idx = parseInt(e.target.dataset.idx);
    const valSeconds = parseFloat(e.target.value);

    if (isNaN(valSeconds) || valSeconds === 0) return;

    const seg = state.segments[idx];
    const oldStart = seg.start;
    const newStart = oldStart + valSeconds;

    // Find limit (Next Locked Segment or Total Duration)
    let limitTime = state.duration;
    const nextAnchorIdx = state.segments.findIndex((s, i) => i > idx && s.locked);
    if (nextAnchorIdx !== -1) {
        limitTime = state.segments[nextAnchorIdx].start;
    }

    // Validate New Start
    if (newStart >= limitTime) {
        alert(`Cannot shift start beyond limit (${formatTime(limitTime)}).`);
        e.target.value = ""; // Clear input
        return;
    }

    if (newStart < 0) {
        alert("Cannot shift start before 00:00:00.");
        e.target.value = "";
        return;
    }

    // Update Start
    seg.start = newStart;

    // Update End to preserve duration
    const duration = seg.end - oldStart;
    seg.end = seg.start + duration;

    // Update previous segment end if not locked
    if (idx > 0) {
        const prev = state.segments[idx - 1];
        if (!prev.locked) {
            prev.end = seg.start;
        } else if (seg.start < prev.end) {
            // Conflict with locked previous
            alert("Cannot shift start before previous locked segment end.");
            // Revert
            seg.start = oldStart;
            seg.end = oldStart + duration;
            e.target.value = "";
            renderSegments();
            return;
        }
    }

    // Cascade from this segment
    cascadeFrom(idx);
    renderSegments();
}

function handleTimeChange(e) {
    const idx = parseInt(e.target.dataset.idx);
    const field = e.target.dataset.field;
    const val = parseTime(e.target.value);
    const seg = state.segments[idx];

    if (field === 'start') {
        // Validate against previous segment if locked
        if (idx > 0) {
            const prev = state.segments[idx - 1];
            if (prev.locked && val < prev.end) {
                alert("Cannot move start before previous locked segment end.");
                renderSegments(); // Revert
                return;
            }
            // If previous is not locked, we update its end
            if (!prev.locked) {
                prev.end = val;
            }
        }
        seg.start = val;
        // If start > end, push end?
        if (seg.start >= seg.end) {
            seg.end = seg.start + 60; // Default push
        }
    } else {
        // Changing End
        if (val <= seg.start) {
            alert("End time must be greater than start time.");
            renderSegments();
            return;
        }
        seg.end = val;

        // Cascade: Regenerate segments from here to next anchor
        cascadeFrom(idx);
    }
    renderSegments();
}

function cascadeFrom(idx) {
    const currentSeg = state.segments[idx];
    const nextAnchorIdx = state.segments.findIndex((s, i) => i > idx && s.locked);

    let limitTime = state.duration;
    let limitIdx = state.segments.length;

    if (nextAnchorIdx !== -1) {
        limitTime = state.segments[nextAnchorIdx].start;
        limitIdx = nextAnchorIdx;
    }

    // If current segment overlaps next anchor, clamp it
    if (currentSeg.end > limitTime) {
        currentSeg.end = limitTime;
    }

    // Now regenerate segments between currentSeg.end and limitTime
    const segLen = getSegmentLength() || 60; // Fallback
    const newSegs = [];
    let t = currentSeg.end;
    let tempIdx = 1; // For naming

    while (t < limitTime - 0.1) {
        let nextEnd = Math.min(t + segLen, limitTime);
        newSegs.push({
            id: Date.now() + Math.random(),
            start: t,
            end: nextEnd,
            locked: false,
            outputName: `segment_auto_${Date.now().toString().slice(-4)}` // Temp name
        });
        t = nextEnd;
    }

    // Replace segments between idx+1 and limitIdx
    // Remove old ones
    const removeCount = limitIdx - (idx + 1);
    state.segments.splice(idx + 1, removeCount, ...newSegs);

    // Renumber segments to ensure consistent naming
    renumberSegments();
}

function renumberSegments() {
    let autoIdx = 1;
    state.segments.forEach(seg => {
        // If segment is auto-generated (not locked), we enforce the naming convention
        if (!seg.locked) {
            // Find the first available index
            // Actually, simply effectively counting up is usually what users want for "Auto"
            // pattern: segment_01, segment_02, ...

            // However, we must respect existing names if they were manually renamed?
            // The constraint "segment_auto_..." suggests we should only target those or target all unlocked.
            // Let's target all unlocked to force the "stt index" pattern the user wants.

            seg.outputName = `segment_${autoIdx.toString().padStart(2, '0')}`;
        }
        autoIdx++;
    });
}

// Audio & Preview
// Removed as per request

// Export
function checkExportReady() {
    const ready = state.segments.length > 0 && state.outputFolder;
    els.exportBtn.disabled = !ready;
    els.exportZipBtn.disabled = !ready;
}




async function exportSegments(createZip) {
    els.exportBtn.disabled = true;
    els.exportZipBtn.disabled = true;
    els.exportStatus.textContent = "Exporting...";

    try {
        const res = await fetch('/api/split', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                inputFile: state.filePath,
                outputDir: state.outputFolder,
                segments: state.segments,
                createZip: createZip
            })
        });
        const data = await res.json();
        if (data.success) {
            let msg = `Success! Created ${data.created.length} files.`;
            if (data.zipPath) {
                msg += `\nZip saved to ${data.zipPath}`;
            }
            alert(msg);
            els.exportStatus.textContent = "";
            if (data.errors.length > 0) {
                alert("Some errors occurred:\n" + data.errors.join('\n'));
            }
        } else {
            els.exportStatus.textContent = "Export failed: " + data.error;
        }
    } catch (err) {
        els.exportStatus.textContent = "Export failed: " + err;
    } finally {
        checkExportReady();
    }
}
