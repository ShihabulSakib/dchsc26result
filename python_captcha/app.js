(function () {
  "use strict";

  const CACHE_KEY = "dc_hsc2026_results_cache_v2";
  const DATA_URL = "students_data.json";
  const PROGRESS_JSONL_URL = "results/marksheets_20261106_104600/progress.jsonl";
  const ASSIGNED_JSON_URL = "assigned_hsc_rolls_862.json";

  const PCM_CODES = new Set(["174-175", "176-177", "265-266"]);
  const PCM_KEYWORDS = ["PHYSICS", "CHEMISTRY", "HIGHER MATHEMATICS", "MATHEMATICS"];

  const SECTION_INFO = {
    ALL: { label: "All Sections", range: "1202425010001 – 1202425010900", start: 1, end: 900 },
    A: { label: "Section A", range: "1202425010001 – 1202425010150", start: 1, end: 150 },
    B: { label: "Section B", range: "1202425010151 – 1202425010300", start: 151, end: 300 },
    C: { label: "Section C", range: "1202425010301 – 1202425010450", start: 301, end: 450 },
    D: { label: "Section D", range: "1202425010451 – 1202425010600", start: 451, end: 600 },
    E: { label: "Section E", range: "1202425010601 – 1202425010750", start: 601, end: 750 },
    F: { label: "Section F", range: "1202425010751 – 1202425010900", start: 751, end: 900 },
  };

  const defaultPageSize = window.innerWidth <= 680 ? 25 : 50;

  const state = {
    meta: null,
    students: [],
    filteredStudents: [],
    byRoll: new Map(),
    sectionFilter: "ALL", // 'ALL' | 'A' | 'B' | 'C' | 'D' | 'E' | 'F'
    sortBy: "total_marks", // 'total_marks' | 'pcm_percentile' | 'college_roll'
    statusFilter: "with_marks", // 'with_marks' | 'gpa_5' | 'all'
    searchQuery: "",
    currentPage: 1,
    pageSize: defaultPageSize,
    activeView: "loading", // 'loading' | 'directory' | 'marksheet'
    currentRoll: null,
    savedScrollY: 0,
    pushedMarksheetHistory: false,
  };

  // DOM Elements
  const els = {
    loadingView: document.getElementById("loadingView"),
    loadingSubText: document.getElementById("loadingSubText"),
    directoryView: document.getElementById("directoryView"),
    marksheetView: document.getElementById("marksheetView"),
    cacheStatusText: document.getElementById("cacheStatusText"),
    refreshCacheBtn: document.getElementById("refreshCacheBtn"),
    globalPrintBtn: document.getElementById("globalPrintBtn"),
    brandHomeBtn: document.getElementById("brandHomeBtn"),
    statStudentsLabel: document.getElementById("statStudentsLabel"),
    statTotalStudents: document.getElementById("statTotalStudents"),
    statTotalMeta: document.getElementById("statTotalMeta"),
    statGpa5Count: document.getElementById("statGpa5Count"),
    statGpa5Pct: document.getElementById("statGpa5Pct"),
    statHighestTotal: document.getElementById("statHighestTotal"),
    statHighestTotalName: document.getElementById("statHighestTotalName"),
    statHighestPcm: document.getElementById("statHighestPcm"),
    statHighestPcmName: document.getElementById("statHighestPcmName"),
    activeSectionRangeText: document.getElementById("activeSectionRangeText"),
    sectionPillsContainer: document.getElementById("sectionPillsContainer"),
    searchInput: document.getElementById("searchInput"),
    clearSearchBtn: document.getElementById("clearSearchBtn"),
    sortMarksBtn: document.getElementById("sortMarksBtn"),
    sortPcmBtn: document.getElementById("sortPcmBtn"),
    sortRollBtn: document.getElementById("sortRollBtn"),
    statusFilterSelect: document.getElementById("statusFilterSelect"),
    resultsCountText: document.getElementById("resultsCountText"),
    tableCardTop: document.getElementById("tableCardTop"),
    rankColHeader: document.getElementById("rankColHeader"),
    studentsTableBody: document.getElementById("studentsTableBody"),
    emptyTableState: document.getElementById("emptyTableState"),
    paginationBar: document.getElementById("paginationBar"),
    paginationInfoText: document.getElementById("paginationInfoText"),
    prevPageBtn: document.getElementById("prevPageBtn"),
    nextPageBtn: document.getElementById("nextPageBtn"),
    pageNumbersContainer: document.getElementById("pageNumbersContainer"),
    pageSizeSelect: document.getElementById("pageSizeSelect"),
    backToListBtn: document.getElementById("backToListBtn"),
    prevStudentBtn: document.getElementById("prevStudentBtn"),
    nextStudentBtn: document.getElementById("nextStudentBtn"),
    printMarksheetBtn: document.getElementById("printMarksheetBtn"),
    marksheetArticle: document.getElementById("marksheetArticle"),
  };

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function cleanSpaces(text) {
    if (!text) return "";
    return String(text).replace(/\s+/g, " ").trim();
  }

  function getSectionFromRoll(collegeRoll) {
    const digits = String(collegeRoll || "").replace(/\D/g, "");
    const rollNum = digits.length >= 4 ? parseInt(digits.slice(-4), 10) : 0;
    for (const sec of ["A", "B", "C", "D", "E", "F"]) {
      const info = SECTION_INFO[sec];
      if (rollNum >= info.start && rollNum <= info.end) {
        return sec;
      }
    }
    return "Other";
  }

  // Fallback parser if reading progress.jsonl + assigned_hsc_rolls_862.json directly in browser
  function parseSubjectString(rawStr) {
    if (!rawStr || typeof rawStr !== "string") return [];
    const subjects = [];
    const parts = rawStr.split(",");
    for (const rawPart of parts) {
      const part = rawPart.trim();
      if (!part) continue;
      const m = part.match(/^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)\s+(\d+)$/);
      if (m) {
        const code = m[1];
        const grade = m[2];
        const subject = cleanSpaces(m[3]);
        const marksStr = m[4];
        const marks = parseInt(marksStr, 10) || 0;
        const maxMarks = code === "275" ? 100 : 200;
        const isPcm =
          PCM_CODES.has(code) ||
          PCM_KEYWORDS.some((kw) => subject.toUpperCase().includes(kw));
        subjects.push({
          code,
          subject,
          grade,
          marks,
          marks_display: marksStr,
          max_marks: maxMarks,
          is_pcm: isPcm,
        });
        continue;
      }
      const mNoMarks = part.match(/^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)$/);
      if (mNoMarks) {
        const code = mNoMarks[1];
        const grade = mNoMarks[2];
        const subject = cleanSpaces(mNoMarks[3]);
        const maxMarks = code === "275" ? 100 : 200;
        const isPcm =
          PCM_CODES.has(code) ||
          PCM_KEYWORDS.some((kw) => subject.toUpperCase().includes(kw));
        subjects.push({
          code,
          subject,
          grade,
          marks: 0,
          marks_display: "—",
          max_marks: maxMarks,
          is_pcm: isPcm,
        });
      }
    }
    return subjects;
  }

  function buildFromRawFiles(assignedList, progressText) {
    const recordsBySerial = new Map();
    if (Array.isArray(assignedList)) {
      for (const rec of assignedList) {
        if (rec && rec.serial_no != null) {
          recordsBySerial.set(Number(rec.serial_no), rec);
        }
      }
    }
    const progressBySerial = new Map();
    for (const line of String(progressText || "").split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const item = JSON.parse(trimmed);
        if (item && item.serial_no != null) {
          progressBySerial.set(Number(item.serial_no), item);
        }
      } catch (_err) {
        // Ignore partial line while scraping
      }
    }

    const serials = Array.from(
      new Set([...recordsBySerial.keys(), ...progressBySerial.keys()])
    ).sort((a, b) => a - b);

    const students = serials.map((serial) => {
      const rec = recordsBySerial.get(serial) || {};
      const prog = progressBySerial.get(serial) || {};
      const info = prog.info || {};
      const status = prog.status || (Object.keys(prog).length ? "unknown" : "pending");
      const name = cleanSpaces(
        info.name || prog.returned_name || rec.name || `Student #${serial}`
      );
      const collegeRoll = String(
        rec.roll || `120242501${String(serial).padStart(4, "0")}`
      ).trim();
      const shortRoll = collegeRoll.length >= 4 ? collegeRoll.slice(-4) : String(serial);
      const section = getSectionFromRoll(collegeRoll);

      let resultRaw = prog.result_raw || "";
      if (!resultRaw && prog.raw && prog.raw.result && prog.raw.result.result) {
        resultRaw = prog.raw.result.result;
      }
      const subjects = parseSubjectString(resultRaw);
      const totalMarks = subjects.reduce((sum, s) => sum + (s.marks || 0), 0);

      let physicsMarks = 0;
      let chemistryMarks = 0;
      let mathMarks = 0;
      for (const s of subjects) {
        const upper = s.subject.toUpperCase();
        if (s.code === "174-175" || upper.includes("PHYSICS")) physicsMarks = s.marks;
        else if (s.code === "176-177" || upper.includes("CHEMISTRY")) chemistryMarks = s.marks;
        else if (s.code === "265-266" || upper.includes("MATHEMATICS")) mathMarks = s.marks;
      }
      const pcmMarks = physicsMarks + chemistryMarks + mathMarks;
      const pcmPercentile = subjects.length
        ? Math.round((pcmMarks / 6) * 100) / 100
        : 0;

      const rawGpa = info.gpa || prog.gpa || null;
      const gpaNum = rawGpa !== null && !isNaN(Number(rawGpa)) ? Number(rawGpa) : null;

      return {
        serial_no: serial,
        college_roll: collegeRoll,
        short_roll: shortRoll,
        section,
        name,
        group: cleanSpaces(info.groupName || rec.student_group || "SCIENCE").toUpperCase(),
        session: cleanSpaces(info.session || rec.session || "2024-25"),
        institute: cleanSpaces(info.instituteName || "DHAKA COLLEGE"),
        pass_year: info.passYear || 2026,
        status,
        result: info.result || (gpaNum !== null ? "P" : status === "ok" ? "F" : null),
        gpa: gpaNum !== null ? gpaNum.toFixed(2) : rawGpa ? String(rawGpa) : null,
        gpa_value: gpaNum !== null ? gpaNum : -1,
        total_marks: totalMarks,
        max_total_marks: 1300,
        pcm_marks: pcmMarks,
        max_pcm_marks: 600,
        pcm_percentile: pcmPercentile,
        physics_marks: physicsMarks,
        chemistry_marks: chemistryMarks,
        math_marks: mathMarks,
        subjects,
      };
    });

    assignRanks(students);
    const okStudents = students.filter((s) => s.total_marks > 0);
    return {
      meta: {
        title: "Dhaka College HSC 2026 Results",
        institute: "Dhaka College",
        session: "2024-25",
        exam: "HSC 2026",
        group: "Science",
        generated_at: new Date().toISOString(),
        total_students: students.length,
        with_marksheets: okStudents.length,
        gpa_5_count: okStudents.filter((s) => s.gpa === "5.00").length,
        highest_total: okStudents.reduce((m, s) => Math.max(m, s.total_marks), 0),
        highest_pcm_percentile: okStudents.reduce(
          (m, s) => Math.max(m, s.pcm_percentile),
          0
        ),
      },
      students,
    };
  }

  function assignRanks(students) {
    for (const s of students) {
      if (!s.section) {
        s.section = getSectionFromRoll(s.college_roll);
      }
    }

    const withMarks = students.filter((s) => s.total_marks > 0);

    const byMarks = [...withMarks].sort(
      (a, b) =>
        b.total_marks - a.total_marks ||
        b.pcm_marks - a.pcm_marks ||
        b.gpa_value - a.gpa_value ||
        a.serial_no - b.serial_no
    );
    let currentRank = 0;
    let lastScore = null;
    byMarks.forEach((s, idx) => {
      if (s.total_marks !== lastScore) {
        currentRank = idx + 1;
        lastScore = s.total_marks;
      }
      s.marks_rank = currentRank;
    });

    const byPcm = [...withMarks].sort(
      (a, b) =>
        b.pcm_marks - a.pcm_marks ||
        b.total_marks - a.total_marks ||
        b.gpa_value - a.gpa_value ||
        a.serial_no - b.serial_no
    );
    let currentPcmRank = 0;
    let lastPcm = null;
    byPcm.forEach((s, idx) => {
      if (s.pcm_marks !== lastPcm) {
        currentPcmRank = idx + 1;
        lastPcm = s.pcm_marks;
      }
      s.pcm_rank = currentPcmRank;
    });

    // Assign per-section ranks (A - F)
    for (const sec of ["A", "B", "C", "D", "E", "F"]) {
      const secMarks = byMarks.filter((s) => s.section === sec);
      let rM = 0;
      let lastM = null;
      secMarks.forEach((s, idx) => {
        if (s.total_marks !== lastM) {
          rM = idx + 1;
          lastM = s.total_marks;
        }
        s.section_marks_rank = rM;
      });

      const secPcm = byPcm.filter((s) => s.section === sec);
      let rP = 0;
      let lastP = null;
      secPcm.forEach((s, idx) => {
        if (s.pcm_marks !== lastP) {
          rP = idx + 1;
          lastP = s.pcm_marks;
        }
        s.section_pcm_rank = rP;
      });
    }
  }

  async function loadDataset(forceNetwork = false) {
    if (!forceNetwork) {
      try {
        const cachedRaw = localStorage.getItem(CACHE_KEY);
        if (cachedRaw) {
          const parsed = JSON.parse(cachedRaw);
          if (parsed && Array.isArray(parsed.students) && parsed.students.length > 0) {
            els.cacheStatusText.textContent = `Cached (${
              parsed.meta?.with_marksheets || parsed.students.length
            } marksheets)`;
            return parsed;
          }
        }
      } catch (_err) {
        // Ignore storage errors
      }
    }

    els.cacheStatusText.textContent = "Fetching JSON…";
    els.loadingSubText.textContent = "Downloading and caching student dataset…";

    let data = null;
    try {
      const resp = await fetch(
        forceNetwork ? `${DATA_URL}?t=${Date.now()}` : DATA_URL,
        { cache: forceNetwork ? "no-cache" : "default" }
      );
      if (resp.ok) {
        data = await resp.json();
      }
    } catch (_err) {
      // Fallback to live JSONL if students_data.json is not found
    }

    if (!data || forceNetwork) {
      try {
        const [progResp, assignedResp] = await Promise.all([
          fetch(`${PROGRESS_JSONL_URL}?t=${Date.now()}`, { cache: "no-store" }),
          fetch(ASSIGNED_JSON_URL),
        ]);
        if (progResp.ok && assignedResp.ok) {
          const [progText, assignedJson] = await Promise.all([
            progResp.text(),
            assignedResp.json(),
          ]);
          const liveBuilt = buildFromRawFiles(assignedJson, progText);
          if (
            !data ||
            (liveBuilt.meta?.with_marksheets || 0) >= (data.meta?.with_marksheets || 0)
          ) {
            data = liveBuilt;
          }
        }
      } catch (_err) {
        // Static deployment uses students_data.json
      }
    }

    if (!data || !Array.isArray(data.students)) {
      throw new Error("Could not load student result JSON.");
    }

    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));
      els.cacheStatusText.textContent = `Cached (${
        data.meta?.with_marksheets || data.students.length
      } marksheets)`;
    } catch (_err) {
      els.cacheStatusText.textContent = `Loaded (${
        data.meta?.with_marksheets || data.students.length
      } marksheets)`;
    }

    return data;
  }

  function hydrateData(payload) {
    state.meta = payload.meta || {};
    state.students = payload.students || [];
    assignRanks(state.students);

    state.byRoll.clear();
    for (const s of state.students) {
      state.byRoll.set(String(s.college_roll), s);
      state.byRoll.set(String(s.serial_no), s);
    }

    renderSummaryCards();
    applyFiltersAndRenderTable();
  }

  function renderSummaryCards() {
    const isAllSec = state.sectionFilter === "ALL";
    const cohort = isAllSec
      ? state.students
      : state.students.filter((s) => s.section === state.sectionFilter);
    const withMarks = cohort.filter((s) => s.total_marks > 0);
    const gpa5Count = withMarks.filter((s) => s.gpa === "5.00").length;

    let topMarksStudent = null;
    let topPcmStudent = null;
    for (const s of withMarks) {
      if (!topMarksStudent || s.total_marks > topMarksStudent.total_marks) {
        topMarksStudent = s;
      }
      if (!topPcmStudent || s.pcm_marks > topPcmStudent.pcm_marks) {
        topPcmStudent = s;
      }
    }

    els.statStudentsLabel.textContent = isAllSec
      ? "Marksheets Loaded"
      : `Section ${state.sectionFilter} Marksheets`;
    els.statTotalStudents.textContent = withMarks.length.toLocaleString();
    els.statTotalMeta.textContent = `Out of ${cohort.length} enrolled`;

    els.statGpa5Count.textContent = gpa5Count.toLocaleString();
    const gpa5Pct = withMarks.length
      ? ((gpa5Count / withMarks.length) * 100).toFixed(1)
      : "0.0";
    els.statGpa5Pct.textContent = `${gpa5Pct}% of appeared students`;

    if (topMarksStudent) {
      els.statHighestTotal.textContent = `${topMarksStudent.total_marks} / 1300`;
      els.statHighestTotalName.textContent = topMarksStudent.name;
    } else {
      els.statHighestTotal.textContent = "—";
      els.statHighestTotalName.textContent = "Out of 1300";
    }

    if (topPcmStudent) {
      els.statHighestPcm.textContent = `${topPcmStudent.pcm_percentile.toFixed(2)}%`;
      els.statHighestPcmName.textContent = `${topPcmStudent.pcm_marks} / 600 (${topPcmStudent.name})`;
    } else {
      els.statHighestPcm.textContent = "—";
      els.statHighestPcmName.textContent = "Physics + Chem + Math";
    }

    const secMeta = SECTION_INFO[state.sectionFilter] || SECTION_INFO.ALL;
    els.activeSectionRangeText.textContent = `${secMeta.label} (Rolls ${secMeta.range})`;
  }

  function applyFiltersAndRenderTable() {
    const q = state.searchQuery.trim().toLowerCase();

    const filtered = state.students.filter((s) => {
      if (state.sectionFilter !== "ALL" && s.section !== state.sectionFilter) {
        return false;
      }
      if (state.statusFilter === "with_marks" && s.total_marks <= 0) return false;
      if (state.statusFilter === "gpa_5" && s.gpa !== "5.00") return false;

      if (!q) return true;
      const nameMatch = s.name.toLowerCase().includes(q);
      const rollMatch = String(s.college_roll).toLowerCase().includes(q);
      const shortMatch =
        String(s.short_roll).toLowerCase() === q || String(s.serial_no) === q;
      return nameMatch || rollMatch || shortMatch;
    });

    filtered.sort((a, b) => {
      if (state.sortBy === "total_marks") {
        if (b.total_marks !== a.total_marks) return b.total_marks - a.total_marks;
        if (b.pcm_marks !== a.pcm_marks) return b.pcm_marks - a.pcm_marks;
        if (b.gpa_value !== a.gpa_value) return b.gpa_value - a.gpa_value;
        return a.serial_no - b.serial_no;
      }
      if (state.sortBy === "pcm_percentile") {
        if (b.pcm_marks !== a.pcm_marks) return b.pcm_marks - a.pcm_marks;
        if (b.total_marks !== a.total_marks) return b.total_marks - a.total_marks;
        if (b.gpa_value !== a.gpa_value) return b.gpa_value - a.gpa_value;
        return a.serial_no - b.serial_no;
      }
      return String(a.college_roll).localeCompare(String(b.college_roll));
    });

    state.filteredStudents = filtered;

    const totalItems = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / state.pageSize));
    if (state.currentPage > totalPages) {
      state.currentPage = totalPages;
    }
    if (state.currentPage < 1) {
      state.currentPage = 1;
    }

    renderTableCurrentPage();
  }

  function renderTableCurrentPage() {
    const filtered = state.filteredStudents;
    const totalItems = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / state.pageSize));
    const startIdx = (state.currentPage - 1) * state.pageSize;
    const endIdx = Math.min(startIdx + state.pageSize, totalItems);
    const pageSlice = filtered.slice(startIdx, endIdx);

    const isSectionFiltered = state.sectionFilter !== "ALL";

    if (state.sortBy === "total_marks") {
      els.rankColHeader.textContent = isSectionFiltered
        ? `Sec ${state.sectionFilter} Rank`
        : "Marks Rank";
    } else if (state.sortBy === "pcm_percentile") {
      els.rankColHeader.textContent = isSectionFiltered
        ? `Sec ${state.sectionFilter} PCM`
        : "PCM Rank";
    } else {
      els.rankColHeader.textContent = "SL";
    }

    const secSuffix = isSectionFiltered ? ` in Section ${state.sectionFilter}` : "";
    els.resultsCountText.textContent =
      totalItems > 0
        ? `Showing ${startIdx + 1}–${endIdx} of ${totalItems} student${
            totalItems === 1 ? "" : "s"
          }${secSuffix}`
        : `No students found${secSuffix}`;

    if (totalItems === 0) {
      els.studentsTableBody.innerHTML = "";
      els.emptyTableState.classList.remove("view-hidden");
      els.paginationBar.classList.add("view-hidden");
      return;
    }

    els.emptyTableState.classList.add("view-hidden");
    els.paginationBar.classList.remove("view-hidden");

    const rowsHtml = pageSlice
      .map((s) => {
        let rankNum = s.serial_no;
        let globalSubRank = "";
        if (state.sortBy === "total_marks") {
          rankNum = isSectionFiltered
            ? s.section_marks_rank || "—"
            : s.marks_rank || "—";
          if (isSectionFiltered && s.marks_rank) {
            globalSubRank = `All #${s.marks_rank}`;
          }
        } else if (state.sortBy === "pcm_percentile") {
          rankNum = isSectionFiltered
            ? s.section_pcm_rank || "—"
            : s.pcm_rank || "—";
          if (isSectionFiltered && s.pcm_rank) {
            globalSubRank = `All #${s.pcm_rank}`;
          }
        }

        let rankBadgeClass = "rank-badge";
        if (rankNum === 1) rankBadgeClass += " top-1";
        else if (rankNum === 2) rankBadgeClass += " top-2";
        else if (rankNum === 3) rankBadgeClass += " top-3";

        const rankLabel = typeof rankNum === "number" ? `#${rankNum}` : rankNum;

        let gpaHtml = `<span class="gpa-pill">—</span>`;
        if (s.gpa) {
          const isMax = s.gpa === "5.00";
          gpaHtml = `<span class="gpa-pill ${
            isMax ? "gpa-max" : ""
          }">GPA ${escapeHtml(s.gpa)}</span>`;
        } else if (s.result === "F" || (s.result && s.result.startsWith("F"))) {
          gpaHtml = `<span class="gpa-pill gpa-fail">F</span>`;
        } else if (s.result === "A") {
          gpaHtml = `<span class="gpa-pill">Absent</span>`;
        } else if (s.status === "missing_roll") {
          gpaHtml = `<span class="gpa-pill">No HSC Roll</span>`;
        }

        const totalDisplay =
          s.total_marks > 0
            ? `<span class="metric-primary">${s.total_marks}</span><span class="metric-sub">/ 1300</span>`
            : `<span class="metric-sub">No marksheet</span>`;

        const pcmDisplay =
          s.pcm_marks > 0
            ? `<span class="metric-primary">${s.pcm_percentile.toFixed(
                2
              )}%</span><span class="metric-sub">${s.pcm_marks} / 600</span>`
            : `<span class="metric-sub">—</span>`;

        return `<tr data-roll="${escapeHtml(
          s.college_roll
        )}" tabindex="0" role="button" aria-label="View marksheet for ${escapeHtml(
          s.name
        )}, College Roll ${escapeHtml(s.college_roll)}, Section ${escapeHtml(s.section)}">
          <td class="rank-cell cell-rank">
            <span class="${rankBadgeClass}">${escapeHtml(rankLabel)}</span>
            ${
              globalSubRank
                ? `<span class="metric-sub" style="margin-top:2px;">${escapeHtml(
                    globalSubRank
                  )}</span>`
                : ""
            }
          </td>
          <td class="cell-name"><span class="student-name">${escapeHtml(
            s.name
          )}</span></td>
          <td class="cell-roll"><span class="roll-mono">${escapeHtml(
            s.college_roll
          )}</span></td>
          <td class="center-col cell-sec"><span class="sec-badge">Sec ${escapeHtml(
            s.section
          )}</span></td>
          <td class="center-col cell-gpa">${gpaHtml}</td>
          <td class="num-col cell-marks">${totalDisplay}</td>
          <td class="num-col cell-pcm">${pcmDisplay}</td>
          <td class="num-col hide-tablet cell-action no-print">
            <span class="view-link">Marksheet &rarr;</span>
          </td>
        </tr>`;
      })
      .join("");

    els.studentsTableBody.innerHTML = rowsHtml;
    renderPaginationControls(totalPages, totalItems, startIdx + 1, endIdx);
  }

  function renderPaginationControls(totalPages, totalItems, startItem, endItem) {
    els.paginationInfoText.textContent = `Page ${state.currentPage} of ${totalPages} (${startItem}–${endItem} of ${totalItems})`;
    els.prevPageBtn.disabled = state.currentPage <= 1;
    els.nextPageBtn.disabled = state.currentPage >= totalPages;

    // Build smart page button list
    const pages = [];
    const maxVisible = window.innerWidth <= 520 ? 5 : 7;
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      const side = window.innerWidth <= 520 ? 0 : 1;
      let left = Math.max(2, state.currentPage - side);
      let right = Math.min(totalPages - 1, state.currentPage + side);

      if (state.currentPage <= 2) {
        right = Math.min(totalPages - 1, 3);
      } else if (state.currentPage >= totalPages - 1) {
        left = Math.max(2, totalPages - 2);
      }

      if (left > 2) pages.push("...");
      for (let i = left; i <= right; i++) pages.push(i);
      if (right < totalPages - 1) pages.push("...");
      pages.push(totalPages);
    }

    els.pageNumbersContainer.innerHTML = pages
      .map((p) => {
        if (p === "...") {
          return `<span class="page-ellipsis">&hellip;</span>`;
        }
        const activeClass = p === state.currentPage ? "active" : "";
        return `<button type="button" class="page-num-btn ${activeClass}" data-page="${p}" aria-label="Page ${p}">${p}</button>`;
      })
      .join("");
  }

  function goToPage(pageNum, scrollToTable = true) {
    const totalPages = Math.max(
      1,
      Math.ceil(state.filteredStudents.length / state.pageSize)
    );
    const clamped = Math.max(1, Math.min(totalPages, pageNum));
    if (clamped === state.currentPage) return;
    state.currentPage = clamped;
    renderTableCurrentPage();

    if (scrollToTable && els.tableCardTop) {
      const rect = els.tableCardTop.getBoundingClientRect();
      const targetY = window.scrollY + rect.top - 72;
      window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
    }
  }

  function renderMarksheet(student) {
    const overallPercentage =
      student.total_marks > 0
        ? ((student.total_marks / 1300) * 100).toFixed(2)
        : "0.00";

    const gpaDisplay = student.gpa
      ? student.gpa
      : student.result === "A"
      ? "Absent"
      : student.result || "N/A";

    const statusBadgeText =
      student.gpa === "5.00"
        ? "GPA 5.00 • Passed"
        : student.gpa
        ? `GPA ${student.gpa} • Passed`
        : student.result === "A"
        ? "Absent"
        : student.result && student.result.startsWith("F")
        ? "Unsuccessful"
        : "Record Unavailable";

    let subjectsRowsHtml = "";
    if (Array.isArray(student.subjects) && student.subjects.length > 0) {
      subjectsRowsHtml = student.subjects
        .map((sub) => {
          const pct =
            sub.marks > 0 && sub.max_marks
              ? `${((sub.marks / sub.max_marks) * 100).toFixed(1)}%`
              : "—";
          const pcmBadge = sub.is_pcm ? `<span class="pcm-tag">PCM</span>` : "";
          return `<tr class="${sub.is_pcm ? "pcm-row" : ""}">
            <td style="font-family: var(--font-mono); font-size: 0.81rem; color: var(--text-secondary);">
              ${escapeHtml(sub.code)}
            </td>
            <td style="font-weight: 500;">
              ${escapeHtml(sub.subject)} ${pcmBadge}
            </td>
            <td class="center-col">
              <span class="gpa-pill ${
                sub.grade === "A+" ? "gpa-max" : sub.grade === "F" ? "gpa-fail" : ""
              }">${escapeHtml(sub.grade)}</span>
            </td>
            <td class="num-col" style="font-family: var(--font-mono); font-weight: 600;">
              ${escapeHtml(sub.marks_display || sub.marks)} <span style="color: var(--text-muted); font-weight: 400; font-size: 0.76rem;">/ ${
            sub.max_marks
          }</span>
            </td>
            <td class="num-col hide-mobile" style="font-family: var(--font-mono); color: var(--text-secondary); font-size: 0.81rem;">
              ${pct}
            </td>
          </tr>`;
        })
        .join("");

      subjectsRowsHtml += `<tr class="Subjects-total-row">
        <td colspan="2">Total Marks (All 7 Subjects)</td>
        <td class="center-col">GPA ${escapeHtml(gpaDisplay)}</td>
        <td class="num-col" style="font-family: var(--font-mono);">
          ${student.total_marks} <span style="color: var(--text-muted); font-weight: 400; font-size: 0.76rem;">/ 1300</span>
        </td>
        <td class="num-col hide-mobile" style="font-family: var(--font-mono);">
          ${overallPercentage}%
        </td>
      </tr>`;
    } else {
      subjectsRowsHtml = `<tr>
        <td colspan="5" class="empty-state">
          Subject-wise marksheet data is not available for this student (${escapeHtml(
            statusBadgeText
          )}).
        </td>
      </tr>`;
    }

    const marksRankSub = student.marks_rank
      ? `Overall #${student.marks_rank}${
          student.section_marks_rank
            ? ` • Sec ${student.section} #${student.section_marks_rank}`
            : ""
        }`
      : "Out of 1300 marks";

    const pcmRankSub = student.pcm_rank
      ? `Overall #${student.pcm_rank}${
          student.section_pcm_rank
            ? ` • Sec ${student.section} #${student.section_pcm_rank}`
            : ""
        }`
      : "Physics + Chem + Math";

    els.marksheetArticle.innerHTML = `
      <div class="sheet-header">
        <div>
          <div class="sheet-institute-label">Academic Transcript &bull; HSC Examination ${escapeHtml(
            student.pass_year
          )}</div>
          <h2 class="sheet-institute-name">${escapeHtml(student.institute)}</h2>
          <div class="sheet-exam-subtitle">
            Higher Secondary Certificate (HSC) &bull; ${escapeHtml(
              student.group
            )} Group &bull; Session ${escapeHtml(student.session)}
          </div>
        </div>
        <div class="sheet-status-stamp">
          <span class="stamp-badge">${escapeHtml(statusBadgeText)}</span>
        </div>
      </div>

      <!-- Privacy-Safe Student Identification (Real Name, College Roll & Section Only) -->
      <div class="identity-grid" aria-label="Student Identification">
        <div>
          <div class="id-item-label">Student Real Name</div>
          <div class="id-item-value">${escapeHtml(student.name)}</div>
        </div>
        <div>
          <div class="id-item-label">College Roll</div>
          <div class="id-item-value mono">${escapeHtml(student.college_roll)}</div>
        </div>
        <div>
          <div class="id-item-label">College Section</div>
          <div class="id-item-value">Section ${escapeHtml(student.section || "—")}</div>
        </div>
        <div>
          <div class="id-item-label">Group &amp; Session</div>
          <div class="id-item-value">${escapeHtml(student.group)} (${escapeHtml(
      student.session
    )})</div>
        </div>
      </div>

      <!-- Summary Performance Metrics -->
      <div class="sheet-metrics-grid">
        <div class="sheet-metric-box">
          <div class="sm-label">Grade Point Average</div>
          <div class="sm-value">${escapeHtml(gpaDisplay)}</div>
          <div class="sm-sub">Out of 5.00 scale</div>
        </div>
        <div class="sheet-metric-box highlighted">
          <div class="sm-label">Total Marks</div>
          <div class="sm-value">${
            student.total_marks > 0 ? `${student.total_marks} / 1300` : "—"
          }</div>
          <div class="sm-sub">${escapeHtml(marksRankSub)}</div>
        </div>
        <div class="sheet-metric-box highlighted">
          <div class="sm-label">PCM Percentile</div>
          <div class="sm-value">${
            student.pcm_marks > 0 ? `${student.pcm_percentile.toFixed(2)}%` : "—"
          }</div>
          <div class="sm-sub">${escapeHtml(pcmRankSub)}</div>
        </div>
        <div class="sheet-metric-box">
          <div class="sm-label">PCM Marks (${student.pcm_marks || 0}/600)</div>
          <div class="sm-value" style="font-size: 1.02rem; margin-top: 0.35rem;">
            P:${student.physics_marks || "—"} &middot; C:${
      student.chemistry_marks || "—"
    } &middot; M:${student.math_marks || "—"}
          </div>
          <div class="sm-sub">200 marks each subject</div>
        </div>
      </div>

      <!-- Subject-wise Marksheet Table -->
      <div class="section-heading">
        <span>Subject-Wise Marks Breakdown</span>
        <span style="font-size: 0.72rem; font-weight: 400; text-transform: none; color: var(--text-muted);">
          7 Subjects &bull; Maximum 1300 Marks
        </span>
      </div>
      <div class="subjects-table-wrap">
        <table class="subjects-table" aria-label="Subject-wise marksheet">
          <thead>
            <tr>
              <th style="width: 100px;">Code</th>
              <th>Subject</th>
              <th class="center-col" style="width: 90px;">Grade</th>
              <th class="num-col" style="width: 145px;">Marks</th>
              <th class="num-col hide-mobile" style="width: 100px;">Score %</th>
            </tr>
          </thead>
          <tbody>
            ${subjectsRowsHtml}
          </tbody>
        </table>
      </div>

      <!-- PCM Formula Box -->
      <div class="pcm-breakdown-card">
        <div>
          <div class="pcm-formula-title">PCM Percentile Calculation</div>
          <div class="pcm-formula-desc">
            Sum of Physics (${student.physics_marks}), Chemistry (${
      student.chemistry_marks
    }), and Higher Mathematics (${
      student.math_marks
    }) divided by 600 &times; 100 (i.e. &divide; 6)
          </div>
        </div>
        <div class="pcm-equation">
          (${student.physics_marks} + ${student.chemistry_marks} + ${
      student.math_marks
    }) &divide; 6 = <strong>${student.pcm_percentile.toFixed(2)}%</strong>
        </div>
      </div>

      <div class="sheet-footer">
        <span>Dhaka College HSC 2026 Official Result Transcript</span>
        <span>Identification by Student Name &amp; College Roll (${escapeHtml(
          student.college_roll
        )} &bull; Section ${escapeHtml(student.section)})</span>
      </div>
    `;

    // Update Prev / Next buttons based on current filtered list
    const idx = state.filteredStudents.findIndex(
      (s) => String(s.college_roll) === String(student.college_roll)
    );
    els.prevStudentBtn.disabled = idx <= 0;
    els.nextStudentBtn.disabled =
      idx === -1 || idx >= state.filteredStudents.length - 1;
  }

  // View Switching & History Management (Supports Android Back button & Backspace/Esc keys)
  function openStudentMarksheet(roll, pushHistory = true, replaceHistory = false) {
    const student = state.byRoll.get(String(roll));
    if (!student) {
      showDirectoryView(false);
      return;
    }

    if (state.activeView === "directory") {
      state.savedScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    }

    state.currentRoll = String(student.college_roll);
    state.activeView = "marksheet";

    renderMarksheet(student);

    els.loadingView.classList.add("view-hidden");
    els.directoryView.classList.add("view-hidden");
    els.marksheetView.classList.remove("view-hidden");

    document.title = `${student.name} (${student.college_roll}) — Marksheet | Dhaka College HSC 2026`;

    const targetHash = `#roll=${encodeURIComponent(student.college_roll)}`;
    if (pushHistory) {
      history.pushState(
        { view: "marksheet", roll: student.college_roll },
        "",
        targetHash
      );
      state.pushedMarksheetHistory = true;
    } else if (replaceHistory) {
      history.replaceState(
        { view: "marksheet", roll: student.college_roll },
        "",
        targetHash
      );
    }

    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function showDirectoryView(restoreScroll = true) {
    state.activeView = "directory";
    state.currentRoll = null;

    els.loadingView.classList.add("view-hidden");
    els.marksheetView.classList.add("view-hidden");
    els.directoryView.classList.remove("view-hidden");

    document.title = "Dhaka College HSC 2026 — Student Results & Rankings";

    if (restoreScroll && state.savedScrollY > 0) {
      window.scrollTo({ top: state.savedScrollY, behavior: "instant" });
    }
  }

  function navigateBackToDirectory() {
    if (state.activeView !== "marksheet") return;
    if (state.pushedMarksheetHistory) {
      state.pushedMarksheetHistory = false;
      history.back();
    } else {
      history.replaceState(
        { view: "directory" },
        "",
        window.location.pathname + window.location.search
      );
      showDirectoryView(true);
    }
  }

  function stepAdjacentStudent(offset) {
    if (state.activeView !== "marksheet" || !state.currentRoll) return;
    const idx = state.filteredStudents.findIndex(
      (s) => String(s.college_roll) === String(state.currentRoll)
    );
    const nextIdx = idx + offset;
    if (nextIdx >= 0 && nextIdx < state.filteredStudents.length) {
      const nextStudent = state.filteredStudents[nextIdx];
      // Keep pagination page synced if the user steps across page boundaries
      state.currentPage = Math.floor(nextIdx / state.pageSize) + 1;
      renderTableCurrentPage();
      openStudentMarksheet(nextStudent.college_roll, false, true);
    }
  }

  function getRollFromHash() {
    const hash = window.location.hash || "";
    const match = hash.match(/^#roll=([^&]+)/);
    return match ? decodeURIComponent(match[1]) : null;
  }

  function bindEvents() {
    // Initialize pageSizeSelect value
    els.pageSizeSelect.value = String(state.pageSize);

    // Section Filter Pills (ALL, A, B, C, D, E, F)
    els.sectionPillsContainer.addEventListener("click", (e) => {
      const pill = e.target.closest(".section-pill[data-section]");
      if (!pill) return;
      const sec = pill.getAttribute("data-section");
      if (!sec || state.sectionFilter === sec) return;

      state.sectionFilter = sec;
      state.currentPage = 1;

      const allPills = els.sectionPillsContainer.querySelectorAll(".section-pill");
      allPills.forEach((p) => p.classList.toggle("active", p === pill));

      renderSummaryCards();
      applyFiltersAndRenderTable();
    });

    // Search input
    els.searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value || "";
      state.currentPage = 1;
      els.clearSearchBtn.classList.toggle("visible", state.searchQuery.length > 0);
      applyFiltersAndRenderTable();
    });

    els.clearSearchBtn.addEventListener("click", () => {
      state.searchQuery = "";
      state.currentPage = 1;
      els.searchInput.value = "";
      els.clearSearchBtn.classList.remove("visible");
      applyFiltersAndRenderTable();
      els.searchInput.focus();
    });

    // Sort buttons
    const sortBtns = [els.sortMarksBtn, els.sortPcmBtn, els.sortRollBtn];
    sortBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const sortMode = btn.getAttribute("data-sort");
        if (!sortMode || state.sortBy === sortMode) return;
        state.sortBy = sortMode;
        state.currentPage = 1;
        sortBtns.forEach((b) => b.classList.toggle("active", b === btn));
        applyFiltersAndRenderTable();
      });
    });

    // Status filter
    els.statusFilterSelect.addEventListener("change", (e) => {
      state.statusFilter = e.target.value;
      state.currentPage = 1;
      applyFiltersAndRenderTable();
    });

    // Pagination buttons
    els.prevPageBtn.addEventListener("click", () => {
      goToPage(state.currentPage - 1, true);
    });

    els.nextPageBtn.addEventListener("click", () => {
      goToPage(state.currentPage + 1, true);
    });

    els.pageNumbersContainer.addEventListener("click", (e) => {
      const btn = e.target.closest(".page-num-btn[data-page]");
      if (!btn) return;
      const targetPage = parseInt(btn.getAttribute("data-page"), 10);
      if (!isNaN(targetPage)) {
        goToPage(targetPage, true);
      }
    });

    els.pageSizeSelect.addEventListener("change", (e) => {
      const newSize = parseInt(e.target.value, 10) || 25;
      state.pageSize = newSize;
      state.currentPage = 1;
      applyFiltersAndRenderTable();
    });

    // Table row click & keyboard enter
    els.studentsTableBody.addEventListener("click", (e) => {
      const tr = e.target.closest("tr[data-roll]");
      if (!tr) return;
      const roll = tr.getAttribute("data-roll");
      if (roll) openStudentMarksheet(roll, true, false);
    });

    els.studentsTableBody.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const tr = e.target.closest("tr[data-roll]");
        if (!tr) return;
        e.preventDefault();
        const roll = tr.getAttribute("data-roll");
        if (roll) openStudentMarksheet(roll, true, false);
      }
    });

    // Back button & brand home button
    els.backToListBtn.addEventListener("click", () => {
      navigateBackToDirectory();
    });

    els.brandHomeBtn.addEventListener("click", () => {
      if (state.activeView === "marksheet") {
        navigateBackToDirectory();
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });

    els.brandHomeBtn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        els.brandHomeBtn.click();
      }
    });

    // Prev / Next student buttons inside marksheet
    els.prevStudentBtn.addEventListener("click", () => stepAdjacentStudent(-1));
    els.nextStudentBtn.addEventListener("click", () => stepAdjacentStudent(1));

    // Print buttons
    els.printMarksheetBtn.addEventListener("click", () => window.print());
    els.globalPrintBtn.addEventListener("click", () => window.print());

    // Sync / Refresh Cache button
    els.refreshCacheBtn.addEventListener("click", async () => {
      els.refreshCacheBtn.disabled = true;
      try {
        const freshData = await loadDataset(true);
        hydrateData(freshData);
        if (state.activeView === "marksheet" && state.currentRoll) {
          const updated = state.byRoll.get(state.currentRoll);
          if (updated) renderMarksheet(updated);
        }
      } catch (_err) {
        els.cacheStatusText.textContent = "Sync failed (using cached)";
      } finally {
        els.refreshCacheBtn.disabled = false;
      }
    });

    // Browser / Android Hardware Back Button via popstate
    window.addEventListener("popstate", (e) => {
      const rollFromHash = getRollFromHash();
      const rollFromState =
        e.state && e.state.view === "marksheet" ? e.state.roll : null;
      const targetRoll = rollFromState || rollFromHash;

      if (targetRoll && state.byRoll.has(String(targetRoll))) {
        openStudentMarksheet(targetRoll, false, false);
      } else {
        state.pushedMarksheetHistory = false;
        showDirectoryView(true);
      }
    });

    // Backward-going keystrokes: Backspace (when not typing), Escape, Alt+ArrowLeft
    window.addEventListener("keydown", (e) => {
      const tag =
        e.target && e.target.tagName ? e.target.tagName.toUpperCase() : "";
      const isEditable =
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        (e.target && e.target.isContentEditable);

      if (state.activeView === "marksheet") {
        if (
          e.key === "Escape" ||
          (!isEditable && e.key === "Backspace") ||
          (e.altKey && e.key === "ArrowLeft")
        ) {
          e.preventDefault();
          navigateBackToDirectory();
          return;
        }
        if (!isEditable && e.key === "ArrowLeft") {
          e.preventDefault();
          stepAdjacentStudent(-1);
          return;
        }
        if (!isEditable && e.key === "ArrowRight") {
          e.preventDefault();
          stepAdjacentStudent(1);
          return;
        }
      }
    });
  }

  async function init() {
    bindEvents();
    try {
      const payload = await loadDataset(false);
      hydrateData(payload);

      const initialRoll = getRollFromHash();
      if (initialRoll && state.byRoll.has(String(initialRoll))) {
        history.replaceState(
          { view: "directory" },
          "",
          window.location.pathname + window.location.search
        );
        openStudentMarksheet(initialRoll, true, false);
      } else {
        history.replaceState(
          { view: "directory" },
          "",
          window.location.pathname + window.location.search
        );
        showDirectoryView(false);
      }
    } catch (err) {
      els.loadingSubText.textContent =
        err && err.message ? err.message : "Failed to load JSON data.";
    }
  }

  init();
})();
