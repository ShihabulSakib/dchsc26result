(function () {
  "use strict";

  const CACHE_KEY = "dc_hsc2026_multigroup_cache_v3";
  const MANIFEST_URL = "data/manifest.json";
  const COMBINED_DATA_URL = "students_data.json";

  const GROUP_CONFIGS = {
    science: {
      key: "science",
      label: "Science",
      subtitle: "Science Division • Session 2024–25",
      dataUrl: "data/science.json",
      rollPrefix: "120242501",
      hasPcm: true,
      sections: [
        { id: "ALL", label: "All Sections", shortHint: "0001–0900", range: "1202425010001 – 1202425010900", start: 1, end: 900 },
        { id: "A", label: "Section A", shortHint: "0001–0150", range: "1202425010001 – 1202425010150", start: 1, end: 150 },
        { id: "B", label: "Section B", shortHint: "0151–0300", range: "1202425010151 – 1202425010300", start: 151, end: 300 },
        { id: "C", label: "Section C", shortHint: "0301–0450", range: "1202425010301 – 1202425010450", start: 301, end: 450 },
        { id: "D", label: "Section D", shortHint: "0451–0600", range: "1202425010451 – 1202425010600", start: 451, end: 600 },
        { id: "E", label: "Section E", shortHint: "0601–0750", range: "1202425010601 – 1202425010750", start: 601, end: 750 },
        { id: "F", label: "Section F", shortHint: "0751–0900", range: "1202425010751 – 1202425010900", start: 751, end: 900 },
      ],
    },
    humanities: {
      key: "humanities",
      label: "Humanities",
      subtitle: "Humanities Division • Session 2024–25",
      dataUrl: "data/humanities.json",
      rollPrefix: "120242503",
      hasPcm: false,
      sections: [
        { id: "ALL", label: "All Humanities", shortHint: "0001–0155", range: "1202425030001 – 1202425030155", start: 1, end: 200 },
        { id: "A", label: "Section A", shortHint: "0001–0155", range: "1202425030001 – 1202425030155", start: 1, end: 200 },
      ],
    },
    business_studies: {
      key: "business_studies",
      label: "Business Studies",
      subtitle: "Business Studies Division • Session 2024–25",
      dataUrl: "data/business_studies.json",
      rollPrefix: "120242502",
      hasPcm: false,
      sections: [
        { id: "ALL", label: "All Business", shortHint: "0001–0150", range: "1202425020001 – 1202425020150", start: 1, end: 200 },
        { id: "A", label: "Section A", shortHint: "0001–0150", range: "1202425020001 – 1202425020150", start: 1, end: 200 },
      ],
    },
    all: {
      key: "all",
      label: "All Divisions",
      subtitle: "All Divisions (Science, Humanities & Business) • Session 2024–25",
      dataUrl: "data/manifest.json + group JSONs",
      rollPrefix: "1202425",
      hasPcm: false,
      sections: [
        { id: "ALL", label: "All Sections", shortHint: "All Rolls", range: "All Divisions & Sections", start: 1, end: 9999 },
        { id: "A", label: "Section A", shortHint: "0001–0155", range: "Section A Across Groups", start: 1, end: 155 },
        { id: "B", label: "Section B", shortHint: "0151–0300", range: "Section B", start: 151, end: 300 },
        { id: "C", label: "Section C", shortHint: "0301–0450", range: "Section C", start: 301, end: 450 },
        { id: "D", label: "Section D", shortHint: "0451–0600", range: "Section D", start: 451, end: 600 },
        { id: "E", label: "Section E", shortHint: "0601–0750", range: "Section E", start: 601, end: 750 },
        { id: "F", label: "Section F", shortHint: "0751–0900", range: "Section F", start: 751, end: 900 },
      ],
    },
  };

  const PCM_CODES = new Set(["174-175", "176-177", "265-266"]);
  const PCM_KEYWORDS = ["PHYSICS", "CHEMISTRY", "HIGHER MATHEMATICS", "MATHEMATICS"];
  const COMPULSORY_CODES = new Set(["101-102", "107-108", "275"]);

  const defaultPageSize = window.innerWidth <= 680 ? 25 : 50;

  const state = {
    groupsData: {
      science: null,
      humanities: null,
      business_studies: null,
    },
    activeGroup: "science", // 'science' | 'humanities' | 'business_studies' | 'all'
    meta: null,
    students: [],
    filteredStudents: [],
    byRollGlobal: new Map(),
    sectionFilter: "ALL",
    sortBy: "total_marks", // 'total_marks' | 'pcm_percentile' | 'gpa' | 'college_roll'
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
    headerSubtitleText: document.getElementById("headerSubtitleText"),
    cacheStatusText: document.getElementById("cacheStatusText"),
    refreshCacheBtn: document.getElementById("refreshCacheBtn"),
    globalPrintBtn: document.getElementById("globalPrintBtn"),
    brandHomeBtn: document.getElementById("brandHomeBtn"),
    activeGroupSourceText: document.getElementById("activeGroupSourceText"),
    groupTabsContainer: document.getElementById("groupTabsContainer"),
    badgeCountScience: document.getElementById("badgeCountScience"),
    subTextScience: document.getElementById("subTextScience"),
    badgeCountHumanities: document.getElementById("badgeCountHumanities"),
    subTextHumanities: document.getElementById("subTextHumanities"),
    badgeCountBusiness: document.getElementById("badgeCountBusiness"),
    subTextBusiness: document.getElementById("subTextBusiness"),
    badgeCountAll: document.getElementById("badgeCountAll"),
    subTextAll: document.getElementById("subTextAll"),
    groupNoticeBanner: document.getElementById("groupNoticeBanner"),
    groupNoticeText: document.getElementById("groupNoticeText"),
    statStudentsLabel: document.getElementById("statStudentsLabel"),
    statTotalStudents: document.getElementById("statTotalStudents"),
    statTotalMeta: document.getElementById("statTotalMeta"),
    statGpa5Count: document.getElementById("statGpa5Count"),
    statGpa5Pct: document.getElementById("statGpa5Pct"),
    statHighestTotal: document.getElementById("statHighestTotal"),
    statHighestTotalName: document.getElementById("statHighestTotalName"),
    statFourthCardLabel: document.getElementById("statFourthCardLabel"),
    statHighestPcm: document.getElementById("statHighestPcm"),
    statHighestPcmName: document.getElementById("statHighestPcmName"),
    sectionFilterBar: document.getElementById("sectionFilterBar"),
    sectionBarLabel: document.getElementById("sectionBarLabel"),
    activeSectionRangeText: document.getElementById("activeSectionRangeText"),
    sectionPillsContainer: document.getElementById("sectionPillsContainer"),
    searchInput: document.getElementById("searchInput"),
    clearSearchBtn: document.getElementById("clearSearchBtn"),
    sortMarksBtn: document.getElementById("sortMarksBtn"),
    sortPcmBtn: document.getElementById("sortPcmBtn"),
    sortRollBtn: document.getElementById("sortRollBtn"),
    statusFilterSelect: document.getElementById("statusFilterSelect"),
    resultsCountText: document.getElementById("resultsCountText"),
    formulaHintText: document.getElementById("formulaHintText"),
    tableCardTop: document.getElementById("tableCardTop"),
    rankColHeader: document.getElementById("rankColHeader"),
    secColHeader: document.getElementById("secColHeader"),
    metricColHeader: document.getElementById("metricColHeader"),
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

  function detectGroupKeyFromRoll(collegeRoll, fallbackGroup = "science") {
    const str = String(collegeRoll || "");
    if (str.length >= 9) {
      const grpCode = str.slice(7, 9);
      if (grpCode === "01") return "science";
      if (grpCode === "02") return "business_studies";
      if (grpCode === "03") return "humanities";
    }
    return fallbackGroup;
  }

  function getSectionFromRoll(collegeRoll, groupKey = "science") {
    const digits = String(collegeRoll || "").replace(/\D/g, "");
    const rollNum = digits.length >= 4 ? parseInt(digits.slice(-4), 10) : 0;
    const gKey = groupKey || detectGroupKeyFromRoll(collegeRoll);
    if (gKey === "science") {
      const secList = GROUP_CONFIGS.science.sections;
      for (const sec of secList) {
        if (sec.id !== "ALL" && rollNum >= sec.start && rollNum <= sec.end) {
          return sec.id;
        }
      }
      return "Other";
    }
    return rollNum <= 200 ? "A" : "B";
  }

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

  function normalizeProfileSubjects(rawSubjects) {
    if (!Array.isArray(rawSubjects)) return [];
    return rawSubjects
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        if (item.code && item.subject) {
          const code = String(item.code).trim();
          const subjName = cleanSpaces(item.subject).toUpperCase();
          const grade = cleanSpaces(item.grade || "—");
          const rawMarks = item.marks;
          const numMarks =
            typeof rawMarks === "number"
              ? rawMarks
              : typeof rawMarks === "string" && /^\d+$/.test(rawMarks.trim())
              ? parseInt(rawMarks.trim(), 10)
              : 0;
          const maxMarks = item.max_marks || (code === "275" ? 100 : 200);
          const isPcm =
            typeof item.is_pcm === "boolean"
              ? item.is_pcm
              : PCM_CODES.has(code) ||
                PCM_KEYWORDS.some((kw) => subjName.includes(kw));
          return {
            ...item,
            code,
            subject: subjName,
            grade,
            marks: numMarks,
            marks_display:
              item.marks_display || (numMarks > 0 ? String(numMarks) : String(rawMarks || "—")),
            max_marks: maxMarks,
            is_pcm: isPcm,
          };
        }
        const p1 = cleanSpaces(item.paper_1 || "");
        const p2 = cleanSpaces(item.paper_2 || "");
        const stype = cleanSpaces(item.type || "");
        const m1 = p1.match(/^(\d+)\s*-\s*(.+)$/);
        const m2 = p2.match(/^(\d+)\s*-\s*(.+)$/);
        const c1 = m1 ? m1[1] : "";
        const n1 = m1 ? m1[2] : p1;
        const c2 = m2 ? m2[1] : "";
        const code = c1 && c2 ? `${c1}-${c2}` : c1 || c2 || "—";
        let subjName = n1.replace(/\s*[12](st|nd)\s*paper\s*$/i, "").trim().toUpperCase();
        if (code === "275" || subjName === "ICT") {
          subjName = "INFORMATION & COMMUNICATION TECHNOLOGY";
        }
        const maxMarks = code === "275" ? 100 : 200;
        const isPcm =
          PCM_CODES.has(code) ||
          PCM_KEYWORDS.some((kw) => subjName.includes(kw));
        return {
          code,
          subject: subjName,
          subject_type: stype,
          grade: "Pending",
          marks: 0,
          marks_display: "Pending",
          max_marks: maxMarks,
          is_pcm: isPcm,
        };
      })
      .filter(Boolean);
  }

  /**
   * Universal Group JSON Normalizer:
   * Accepts:
   *   1) Built web format { meta: {...}, students: [...] }
   *   2) Raw array of scraped marksheet items, eduboard_fetch marksheets.json, or profile items [...]
   *   3) Raw JSONL text (progress.jsonl format)
   * Automatically merges with any existing base student records (names/rolls/subjects)
   * and computes totals, percentages, GPAs, and ranks.
   */
  function normalizeGroupPayload(rawInput, groupKey, existingBaseStudents = []) {
    const cfg = GROUP_CONFIGS[groupKey] || GROUP_CONFIGS.science;

    let rawRecords = [];
    let providedMeta = {};

    if (typeof rawInput === "string") {
      const trimmed = rawInput.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        try {
          const parsed = JSON.parse(trimmed);
          return normalizeGroupPayload(parsed, groupKey, existingBaseStudents);
        } catch (_e) {
          // Fall through to JSONL parser
        }
      }
      for (const line of trimmed.split(/\r?\n/)) {
        const l = line.trim();
        if (!l) continue;
        try {
          rawRecords.push(JSON.parse(l));
        } catch (_err) {
          // Ignore partial line
        }
      }
    } else if (Array.isArray(rawInput)) {
      rawRecords = rawInput;
    } else if (rawInput && typeof rawInput === "object") {
      if (Array.isArray(rawInput.students)) {
        rawRecords = rawInput.students;
        providedMeta = rawInput.meta || {};
      }
    }

    // Index any existing base students by roll and serial_no so raw progress.jsonl can inherit names/rolls
    const baseByRoll = new Map();
    const baseBySerial = new Map();
    if (Array.isArray(existingBaseStudents)) {
      for (const b of existingBaseStudents) {
        if (b.college_roll) baseByRoll.set(String(b.college_roll), b);
        if (b.roll) baseByRoll.set(String(b.roll), b);
        if (b.serial_no != null) baseBySerial.set(Number(b.serial_no), b);
      }
    }

    const students = rawRecords.map((rec, idx) => {
      const src = rec.source || {};
      const ident = rec.identity || {};
      const ms = rec.marksheet || {};
      const ver = rec.verification || {};
      const info = rec.info || {};

      const serial = Number(
        rec.serial_no || src.serial_no || rec.id || idx + 1
      );
      const recRollCandidate =
        rec.college_roll || src.college_roll || rec.roll || "";
      const baseRec =
        (recRollCandidate && baseByRoll.get(String(recRollCandidate))) ||
        baseBySerial.get(serial) ||
        {};

      const collegeRoll = String(
        recRollCandidate ||
          baseRec.college_roll ||
          baseRec.roll ||
          `${cfg.rollPrefix}${String(serial).padStart(4, "0")}`
      ).trim();

      const shortRoll =
        rec.short_roll ||
        (collegeRoll.length >= 4 ? collegeRoll.slice(-4) : String(serial));

      const detectedGroupKey = rec.group_key || detectGroupKeyFromRoll(collegeRoll, groupKey);
      const section = rec.section || getSectionFromRoll(collegeRoll, detectedGroupKey);

      const name = cleanSpaces(
        rec.name ||
          ident.name ||
          src.expected_name ||
          info.name ||
          rec.returned_name ||
          baseRec.name ||
          `Student #${serial}`
      );

      let subjects = [];
      let resultRaw = rec.result_raw || "";
      if (!resultRaw && rec.raw && rec.raw.result && rec.raw.result.result) {
        resultRaw = rec.raw.result.result;
      }

      if (resultRaw) {
        subjects = parseSubjectString(resultRaw);
      } else if (Array.isArray(ms.subjects) && ms.subjects.length > 0) {
        subjects = normalizeProfileSubjects(ms.subjects);
      } else if (Array.isArray(rec.subjects) && rec.subjects.length > 0) {
        subjects = normalizeProfileSubjects(rec.subjects);
      } else if (Array.isArray(rec.result) && rec.result.length > 0) {
        for (const s of rec.result) {
          if (s && s.raw) subjects.push(...parseSubjectString(s.raw));
          else if (s && s.code) subjects.push(s);
        }
      } else if (Array.isArray(baseRec.subjects) && baseRec.subjects.length > 0) {
        subjects = normalizeProfileSubjects(baseRec.subjects);
      }

      const explicitTotal =
        typeof rec.total_marks === "number" && rec.total_marks > 0
          ? rec.total_marks
          : typeof ms.total_marks === "number" && ms.total_marks > 0
          ? ms.total_marks
          : 0;

      const totalMarks =
        explicitTotal > 0
          ? explicitTotal
          : subjects.reduce((sum, s) => sum + (Number(s.marks) || 0), 0);

      let physicsMarks = Number(rec.physics_marks) || 0;
      let chemistryMarks = Number(rec.chemistry_marks) || 0;
      let mathMarks = Number(rec.math_marks) || 0;
      let compulsoryMarks = Number(rec.compulsory_marks) || 0;

      if (!physicsMarks && !chemistryMarks && !mathMarks && totalMarks > 0) {
        for (const s of subjects) {
          const code = String(s.code || "");
          const upper = String(s.subject || "").toUpperCase();
          const mVal = Number(s.marks) || 0;
          if (code === "174-175" || upper.includes("PHYSICS")) physicsMarks = mVal;
          else if (code === "176-177" || upper.includes("CHEMISTRY")) chemistryMarks = mVal;
          else if (code === "265-266" || upper.includes("MATHEMATICS")) mathMarks = mVal;

          if (
            COMPULSORY_CODES.has(code) ||
            upper.includes("BANGLA") ||
            upper.includes("ENGLISH") ||
            upper.includes("COMMUNICATION TECHNOLOGY") ||
            upper === "ICT"
          ) {
            compulsoryMarks += mVal;
          }
        }
      }

      const pcmMarks =
        typeof rec.pcm_marks === "number" && rec.pcm_marks > 0
          ? rec.pcm_marks
          : physicsMarks + chemistryMarks + mathMarks;

      const pcmPercentile =
        typeof rec.pcm_percentile === "number" && rec.pcm_percentile > 0
          ? rec.pcm_percentile
          : pcmMarks > 0
          ? Math.round((pcmMarks / 6) * 100) / 100
          : 0;

      const overallPercentage =
        typeof rec.overall_percentage === "number" && rec.overall_percentage > 0
          ? rec.overall_percentage
          : totalMarks > 0
          ? Math.round((totalMarks / 1300) * 10000) / 100
          : 0;

      const rawGpa =
        rec.gpa ??
        ident.gpa ??
        info.gpa ??
        src.expected_gpa_or_status ??
        rec.board_gpa_or_status ??
        baseRec.gpa ??
        null;
      const gpaNum =
        rawGpa !== null && rawGpa !== "" && !isNaN(Number(rawGpa))
          ? Number(rawGpa)
          : null;

      const status =
        rec.status ||
        ver.fetch_status ||
        (totalMarks > 0 || gpaNum !== null ? "ok" : "pending");

      return {
        serial_no: serial,
        college_roll: collegeRoll,
        short_roll: shortRoll,
        hsc_roll: rec.hsc_roll || src.hsc_roll || baseRec.hsc_roll || null,
        reg_no: rec.reg_no || src.reg_no || baseRec.reg_no || null,
        section,
        name,
        group: cleanSpaces(
          rec.group ||
            ident.group ||
            info.groupName ||
            rec.student_group ||
            baseRec.group ||
            cfg.label
        ).toUpperCase(),
        group_key: detectedGroupKey,
        session: cleanSpaces(
          rec.session || ident.session || info.session || baseRec.session || "2024-25"
        ),
        academic_year: String(rec.academic_year || baseRec.academic_year || "2"),
        institute: cleanSpaces(
          rec.institute || ident.institution || info.instituteName || "DHAKA COLLEGE"
        ),
        pass_year: rec.pass_year || info.passYear || 2026,
        status,
        result:
          rec.result ||
          ident.result_status ||
          info.result ||
          (gpaNum !== null ? "P" : status === "ok" ? "F" : null),
        gpa:
          gpaNum !== null
            ? gpaNum.toFixed(2)
            : rawGpa && !String(rawGpa).startsWith("F")
            ? String(rawGpa)
            : null,
        gpa_value: gpaNum !== null ? gpaNum : -1,
        total_marks: totalMarks,
        max_total_marks: 1300,
        overall_percentage: overallPercentage,
        compulsory_marks: compulsoryMarks,
        pcm_marks: pcmMarks,
        max_pcm_marks: 600,
        pcm_percentile: pcmPercentile,
        physics_marks: physicsMarks,
        chemistry_marks: chemistryMarks,
        math_marks: mathMarks,
        subjects,
      };
    });

    assignRanks(students, groupKey);
    const okStudents = students.filter((s) => s.total_marks > 0);
    const gpa5Total = students.filter((s) => s.gpa === "5.00").length;

    return {
      meta: {
        ...providedMeta,
        title: `Dhaka College HSC 2026 Results — ${cfg.label}`,
        institute: "Dhaka College",
        session: "2024-25",
        exam: "HSC 2026",
        group: cfg.label,
        group_key: groupKey,
        has_pcm: cfg.hasPcm,
        total_students: students.length,
        with_marksheets: okStudents.length,
        scraping_status:
          okStudents.length > 0
            ? "complete"
            : students.length > 0
            ? "in_progress"
            : "pending",
        gpa_5_count: gpa5Total,
        highest_total: okStudents.reduce((m, s) => Math.max(m, s.total_marks), 0),
        highest_overall_percentage: okStudents.reduce(
          (m, s) => Math.max(m, s.overall_percentage || 0),
          0
        ),
        highest_pcm_percentile: okStudents.reduce(
          (m, s) => Math.max(m, s.pcm_percentile || 0),
          0
        ),
      },
      students,
    };
  }

  function assignRanks(students, groupKey = "science") {
    for (const s of students) {
      if (!s.section) {
        s.section = getSectionFromRoll(s.college_roll, s.group_key || groupKey);
      }
      if (!s.overall_percentage && s.total_marks > 0) {
        s.overall_percentage = Math.round((s.total_marks / 1300) * 10000) / 100;
      }
    }

    const withMarks = students.filter((s) => s.total_marks > 0);

    const byMarks = [...withMarks].sort(
      (a, b) =>
        b.total_marks - a.total_marks ||
        b.gpa_value - a.gpa_value ||
        b.pcm_marks - a.pcm_marks ||
        String(a.college_roll).localeCompare(String(b.college_roll))
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
        String(a.college_roll).localeCompare(String(b.college_roll))
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

    // Assign per-section ranks
    const uniqueSecs = Array.from(new Set(students.map((s) => s.section)));
    for (const sec of uniqueSecs) {
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

  async function fetchJsonOrJsonl(url, forceNetwork = false) {
    const targetUrl = forceNetwork ? `${url}?t=${Date.now()}` : url;
    const resp = await fetch(targetUrl, {
      cache: forceNetwork ? "no-cache" : "default",
    });
    if (!resp.ok) return null;
    const text = await resp.text();
    if (!text || !text.trim()) return null;
    try {
      return JSON.parse(text);
    } catch (_e) {
      return text;
    }
  }

  async function loadManifest(forceNetwork = false) {
    try {
      const manifest = await fetchJsonOrJsonl(MANIFEST_URL, forceNetwork);
      if (manifest && Array.isArray(manifest.groups)) {
        for (const g of manifest.groups) {
          if (g.key === "science") {
            els.badgeCountScience.textContent = (g.total_students || 862).toLocaleString();
            els.subTextScience.textContent = `${g.with_marksheets || 850} Marksheets • Sec A–F`;
          } else if (g.key === "humanities") {
            els.badgeCountHumanities.textContent = (g.total_students || 149).toLocaleString();
            els.subTextHumanities.textContent =
              g.with_marksheets > 0
                ? `${g.with_marksheets} Marksheets • Ready`
                : `${g.total_students || 149} Candidates • In Progress`;
          } else if (g.key === "business_studies") {
            els.badgeCountBusiness.textContent = (g.total_students || 141).toLocaleString();
            els.subTextBusiness.textContent =
              g.with_marksheets > 0
                ? `${g.with_marksheets} Marksheets • Ready`
                : `${g.total_students || 141} Candidates • Ready to Fetch`;
          }
        }
        const totalAll = manifest.groups.reduce((acc, g) => acc + (g.total_students || 0), 0);
        const totalMarks = manifest.groups.reduce((acc, g) => acc + (g.with_marksheets || 0), 0);
        els.badgeCountAll.textContent = totalAll.toLocaleString();
        els.subTextAll.textContent = `${totalMarks} Marksheets Combined`;
        return manifest;
      }
    } catch (_err) {
      // Manifest load error ignored
    }
    return null;
  }

  async function loadSingleGroup(groupKey, forceNetwork = false) {
    if (!groupKey || groupKey === "all") return;
    const cfg = GROUP_CONFIGS[groupKey];
    if (!cfg) return;

    if (!forceNetwork && state.groupsData[groupKey]) {
      return state.groupsData[groupKey];
    }

    try {
      const raw = await fetchJsonOrJsonl(cfg.dataUrl, forceNetwork);
      if (raw) {
        state.groupsData[groupKey] = normalizeGroupPayload(raw, groupKey);
        for (const s of state.groupsData[groupKey].students) {
          state.byRollGlobal.set(String(s.college_roll), s);
        }
        updateCacheBadge(true);
        updateGroupTabBadges();
        return state.groupsData[groupKey];
      }
    } catch (_err) {
      // Fallback to combined data
    }

    // Fallback: try students_data.json
    try {
      const combined = await fetchJsonOrJsonl(COMBINED_DATA_URL, forceNetwork);
      if (combined && Array.isArray(combined.students)) {
        const groupStudents = combined.students.filter(
          (s) => s.group_key === groupKey || detectGroupKeyFromRoll(s.college_roll) === groupKey
        );
        state.groupsData[groupKey] = normalizeGroupPayload(groupStudents, groupKey);
        for (const s of state.groupsData[groupKey].students) {
          state.byRollGlobal.set(String(s.college_roll), s);
        }
        updateCacheBadge(true);
        updateGroupTabBadges();
        return state.groupsData[groupKey];
      }
    } catch (_err2) {
      // Ignore
    }
  }

  async function ensureAllGroupsLoaded(forceNetwork = false) {
    const promises = [];
    for (const g of ["science", "humanities", "business_studies"]) {
      if (forceNetwork || !state.groupsData[g]) {
        promises.push(loadSingleGroup(g, forceNetwork));
      }
    }
    await Promise.all(promises);
    rebuildGlobalRollMap();
    updateGroupTabBadges();
  }

  async function loadInitialData(forceNetwork = false) {
    els.cacheStatusText.textContent = "Loading index…";
    els.loadingSubText.textContent = "Loading Dhaka College HSC 2026 Results…";

    // 1. Fetch lightweight manifest (908 bytes) for immediate counts
    await loadManifest(forceNetwork);

    // 2. Identify requested group from URL
    const parsedHash = parseUrlHash();
    const initialGroup =
      parsedHash.group && GROUP_CONFIGS[parsedHash.group]
        ? parsedHash.group
        : parsedHash.roll
        ? detectGroupKeyFromRoll(parsedHash.roll, "science")
        : "science";

    // 3. Load active group on-demand
    if (initialGroup === "all") {
      await ensureAllGroupsLoaded(forceNetwork);
    } else {
      await loadSingleGroup(initialGroup, forceNetwork);
      // Non-blocking background prefetch for remaining cohorts
      setTimeout(() => {
        for (const g of ["science", "humanities", "business_studies"]) {
          if (g !== initialGroup && !state.groupsData[g]) {
            loadSingleGroup(g, false).catch(() => {});
          }
        }
      }, 300);
    }
  }

  function updateCacheBadge(isCached) {
    const totalLoaded =
      (state.groupsData.science?.students.length || 0) +
      (state.groupsData.humanities?.students.length || 0) +
      (state.groupsData.business_studies?.students.length || 0);
    els.cacheStatusText.textContent = `${
      isCached ? "Cached" : "Loaded"
    } (${totalLoaded.toLocaleString()} students)`;
  }

  function rebuildGlobalRollMap() {
    state.byRollGlobal.clear();
    for (const gKey of ["science", "humanities", "business_studies"]) {
      const grp = state.groupsData[gKey];
      if (!grp || !Array.isArray(grp.students)) continue;
      for (const s of grp.students) {
        state.byRollGlobal.set(String(s.college_roll), s);
      }
    }
  }

  function updateGroupTabBadges() {
    const sci = state.groupsData.science;
    const hum = state.groupsData.humanities;
    const bus = state.groupsData.business_studies;

    if (sci) {
      const sciTotal = sci.students.length;
      const sciMarks = sci.meta.with_marksheets;
      els.badgeCountScience.textContent = sciTotal.toLocaleString();
      els.subTextScience.textContent =
        sciMarks > 0
          ? `${sciMarks} Marksheets • Sec A–F`
          : `${sciTotal} Students • Sec A–F`;
    }

    if (hum) {
      const humTotal = hum.students.length;
      const humMarks = hum.meta.with_marksheets;
      els.badgeCountHumanities.textContent = humTotal.toLocaleString();
      els.subTextHumanities.textContent =
        humMarks > 0
          ? `${humMarks} Marksheets • Ready`
          : `${humTotal} Candidates • In Progress`;
    }

    if (bus) {
      const busTotal = bus.students.length;
      const busMarks = bus.meta.with_marksheets;
      els.badgeCountBusiness.textContent = busTotal.toLocaleString();
      els.subTextBusiness.textContent =
        busMarks > 0
          ? `${busMarks} Marksheets • Ready`
          : `${busTotal} Candidates • Ready to Fetch`;
    }

    const allTotal =
      (sci?.students.length || 0) +
      (hum?.students.length || 0) +
      (bus?.students.length || 0);
    const allMarks =
      (sci?.meta.with_marksheets || 0) +
      (hum?.meta.with_marksheets || 0) +
      (bus?.meta.with_marksheets || 0);
    if (allTotal > 0) {
      els.badgeCountAll.textContent = allTotal.toLocaleString();
      els.subTextAll.textContent = `${allMarks} Marksheets Combined`;
    }
  }

  async function activateGroup(groupKey, resetFilters = true) {
    if (!GROUP_CONFIGS[groupKey]) groupKey = "science";
    state.activeGroup = groupKey;
    const cfg = GROUP_CONFIGS[groupKey];

    // Highlight active tab
    const tabs = els.groupTabsContainer.querySelectorAll(".group-tab[data-group]");
    tabs.forEach((tab) => {
      const isAct = tab.getAttribute("data-group") === groupKey;
      tab.classList.toggle("active", isAct);
      tab.setAttribute("aria-selected", isAct ? "true" : "false");
    });

    els.headerSubtitleText.textContent = cfg.subtitle;
    els.activeGroupSourceText.textContent = cfg.dataUrl;

    // Ensure data is loaded
    if (groupKey === "all") {
      await ensureAllGroupsLoaded();
      const combined = [
        ...(state.groupsData.science?.students || []),
        ...(state.groupsData.humanities?.students || []),
        ...(state.groupsData.business_studies?.students || []),
      ];
      assignRanks(combined, "all");
      const okCount = combined.filter((s) => s.total_marks > 0).length;
      state.students = combined;
      state.meta = {
        group: "All Divisions",
        group_key: "all",
        has_pcm: false,
        total_students: combined.length,
        with_marksheets: okCount,
      };
    } else {
      if (!state.groupsData[groupKey]) {
        els.cacheStatusText.textContent = `Loading ${cfg.label}…`;
        await loadSingleGroup(groupKey);
      }
      const grpPayload =
        state.groupsData[groupKey] || normalizeGroupPayload([], groupKey);
      state.students = grpPayload.students || [];
      state.meta = grpPayload.meta || {};
    }

    if (resetFilters) {
      state.sectionFilter = "ALL";
      state.currentPage = 1;

      // Smart default for statusFilter:
      // If marksheets are available, default to 'with_marks';
      // If scraping is still in progress (0 marksheets), show 'all' so enrolled students are visible!
      if ((state.meta.with_marksheets || 0) > 0) {
        state.statusFilter = "with_marks";
      } else {
        state.statusFilter = "all";
      }
      els.statusFilterSelect.value = state.statusFilter;

      // If switching to non-Science while sortBy was pcm_percentile, switch to total_marks
      if (!cfg.hasPcm && state.sortBy === "pcm_percentile") {
        state.sortBy = "total_marks";
      }
    }

    updateDynamicGroupControls(cfg);
    renderSectionPills(cfg);
    renderNoticeBanner(cfg);
    renderSummaryCards();
    applyFiltersAndRenderTable();
  }

  function updateDynamicGroupControls(cfg) {
    const withMarksCount = state.students.filter((s) => s.total_marks > 0).length;
    const gpa5Count = state.students.filter((s) => s.gpa === "5.00").length;
    const totalCount = state.students.length;

    // Update Show dropdown option labels with live counts for the current group
    const opts = els.statusFilterSelect.options;
    if (opts.length >= 3) {
      opts[0].textContent = `With Marksheets (${withMarksCount})`;
      opts[1].textContent = `GPA 5.00 Only (${gpa5Count})`;
      opts[2].textContent = `All Enrolled (${totalCount})`;
    }

    // Update search placeholder with current group's roll prefix
    els.searchInput.placeholder = `Search ${cfg.label} student name or roll (e.g. ${cfg.rollPrefix}0001 or 0001)...`;

    // Update Sort button #2 & Formula hint & Column headers for Science vs Humanities/Business
    if (cfg.hasPcm) {
      els.sortPcmBtn.textContent = "Highest PCM %";
      els.sortPcmBtn.setAttribute("data-sort", "pcm_percentile");
      els.formulaHintText.textContent =
        "PCM Percentile = (Physics + Chem + Math) ÷ 6";
      els.formulaHintText.title =
        "Physics (200) + Chemistry (200) + Higher Math (200) = 600 max";
      els.metricColHeader.textContent = "PCM Percentile";
      els.secColHeader.textContent = "Section";
    } else {
      els.sortPcmBtn.textContent = "Highest GPA";
      els.sortPcmBtn.setAttribute("data-sort", "gpa");
      els.formulaHintText.textContent =
        "Overall Score % = (Total Marks ÷ 1300) × 100";
      els.formulaHintText.title =
        "7 HSC Subjects (6 × 200 + ICT 100) = 1300 max marks";
      els.metricColHeader.textContent =
        withMarksCount > 0 ? "Overall Score %" : "Subjects";
      els.secColHeader.textContent =
        state.activeGroup === "all" ? "Div / Sec" : "Section";
    }

    const sortBtns = [els.sortMarksBtn, els.sortPcmBtn, els.sortRollBtn];
    sortBtns.forEach((b) =>
      b.classList.toggle("active", b.getAttribute("data-sort") === state.sortBy)
    );
  }

  function renderSectionPills(cfg) {
    const sections = cfg.sections || GROUP_CONFIGS.science.sections;
    els.sectionPillsContainer.innerHTML = sections
      .map((sec) => {
        const activeClass = sec.id === state.sectionFilter ? "active" : "";
        return `<button type="button" class="section-pill ${activeClass}" data-section="${escapeHtml(
          sec.id
        )}" title="${escapeHtml(sec.range)}">
          <span class="sec-name">${escapeHtml(sec.label)}</span>
          <span class="sec-roll-hint">${escapeHtml(sec.shortHint)}</span>
        </button>`;
      })
      .join("");

    // Adjust grid columns cleanly based on pill count
    if (sections.length <= 2) {
      els.sectionPillsContainer.style.gridTemplateColumns = `repeat(${sections.length}, minmax(140px, 240px))`;
    } else {
      els.sectionPillsContainer.style.gridTemplateColumns = "";
    }
  }

  function renderNoticeBanner(cfg) {
    const total = state.students.length;
    const withMarks = state.students.filter((s) => s.total_marks > 0).length;

    if (state.activeGroup === "all") {
      els.groupNoticeBanner.classList.add("view-hidden");
      return;
    }

    if (total > 0 && withMarks === 0) {
      els.groupNoticeBanner.classList.remove("view-hidden");
      els.groupNoticeText.innerHTML = `
        <strong>${escapeHtml(
          cfg.label
        )} Marksheet Scraping in Progress:</strong> Currently displaying all <strong>${total}</strong> Academic Year 2 candidate profiles &amp; registered subjects. Once marksheet scraping completes, update <code>dist/${escapeHtml(
        cfg.dataUrl
      )}</code> (or run <code>python3 build_web_data.py</code>) and click <strong>Sync</strong> to populate GPAs, marks &amp; rankings automatically.
      `;
    } else if (total === 0) {
      els.groupNoticeBanner.classList.remove("view-hidden");
      els.groupNoticeText.innerHTML = `
        <strong>${escapeHtml(
          cfg.label
        )} Base Slot Ready:</strong> Drop the scraped JSON dataset into <code>dist/${escapeHtml(
        cfg.dataUrl
      )}</code> and click <strong>Sync</strong> to load student results and rankings.
      `;
    } else {
      els.groupNoticeBanner.classList.add("view-hidden");
    }
  }

  function renderSummaryCards() {
    const cfg = GROUP_CONFIGS[state.activeGroup] || GROUP_CONFIGS.science;
    const isAllSec = state.sectionFilter === "ALL";
    const cohort = isAllSec
      ? state.students
      : state.students.filter((s) => s.section === state.sectionFilter);
    const withMarks = cohort.filter((s) => s.total_marks > 0);
    const appearedWithGpaOrResult = cohort.filter(
      (s) => s.total_marks > 0 || (s.gpa !== null && s.gpa !== undefined) || s.result === "F"
    );
    const gpa5Count = cohort.filter((s) => s.gpa === "5.00").length;

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

    if (withMarks.length > 0) {
      els.statStudentsLabel.textContent = isAllSec
        ? "Marksheets Loaded"
        : `Section ${state.sectionFilter} Marksheets`;
      els.statTotalStudents.textContent = withMarks.length.toLocaleString();
      els.statTotalMeta.textContent = `Out of ${cohort.length} enrolled (${cfg.label})`;
    } else {
      els.statStudentsLabel.textContent = "Candidates Enrolled";
      els.statTotalStudents.textContent = cohort.length.toLocaleString();
      els.statTotalMeta.textContent =
        cohort.length > 0 ? "Marksheet scraping in progress" : `${cfg.label} Cohort`;
    }

    const denom = withMarks.length > 0 ? withMarks.length : appearedWithGpaOrResult.length;
    els.statGpa5Count.textContent =
      denom > 0 ? gpa5Count.toLocaleString() : "—";
    const gpa5Pct = denom > 0 ? ((gpa5Count / denom) * 100).toFixed(1) : "0.0";
    els.statGpa5Pct.textContent =
      denom > 0
        ? `${gpa5Pct}% of appeared students`
        : "Pending board marksheets";

    if (topMarksStudent) {
      els.statHighestTotal.textContent = `${topMarksStudent.total_marks} / 1300`;
      els.statHighestTotalName.textContent = topMarksStudent.name;
    } else {
      els.statHighestTotal.textContent = "—";
      els.statHighestTotalName.textContent = "Out of 1300";
    }

    if (cfg.hasPcm) {
      els.statFourthCardLabel.textContent = "Highest PCM Percentile";
      if (topPcmStudent && topPcmStudent.pcm_marks > 0) {
        els.statHighestPcm.textContent = `${topPcmStudent.pcm_percentile.toFixed(2)}%`;
        els.statHighestPcmName.textContent = `${topPcmStudent.pcm_marks} / 600 (${topPcmStudent.name})`;
      } else {
        els.statHighestPcm.textContent = "—";
        els.statHighestPcmName.textContent = "Physics + Chem + Math";
      }
    } else {
      els.statFourthCardLabel.textContent = "Highest Overall Score %";
      if (topMarksStudent && topMarksStudent.total_marks > 0) {
        const pct = ((topMarksStudent.total_marks / 1300) * 100).toFixed(2);
        els.statHighestPcm.textContent = `${pct}%`;
        els.statHighestPcmName.textContent = `${topMarksStudent.total_marks} / 1300 (${topMarksStudent.name})`;
      } else {
        els.statHighestPcm.textContent = "—";
        els.statHighestPcmName.textContent = "7 HSC Subjects (1300 Max)";
      }
    }

    const secList = cfg.sections || GROUP_CONFIGS.science.sections;
    const secMeta =
      secList.find((x) => x.id === state.sectionFilter) || secList[0];
    els.activeSectionRangeText.textContent = `${secMeta.label} (${secMeta.range})`;
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
      const groupMatch = String(s.group || "").toLowerCase().includes(q);
      return nameMatch || rollMatch || shortMatch || groupMatch;
    });

    filtered.sort((a, b) => {
      if (state.sortBy === "total_marks") {
        if (b.total_marks !== a.total_marks) return b.total_marks - a.total_marks;
        if (b.gpa_value !== a.gpa_value) return b.gpa_value - a.gpa_value;
        if (b.pcm_marks !== a.pcm_marks) return b.pcm_marks - a.pcm_marks;
        return String(a.college_roll).localeCompare(String(b.college_roll));
      }
      if (state.sortBy === "pcm_percentile") {
        if (b.pcm_marks !== a.pcm_marks) return b.pcm_marks - a.pcm_marks;
        if (b.total_marks !== a.total_marks) return b.total_marks - a.total_marks;
        if (b.gpa_value !== a.gpa_value) return b.gpa_value - a.gpa_value;
        return String(a.college_roll).localeCompare(String(b.college_roll));
      }
      if (state.sortBy === "gpa") {
        if (b.gpa_value !== a.gpa_value) return b.gpa_value - a.gpa_value;
        if (b.total_marks !== a.total_marks) return b.total_marks - a.total_marks;
        return String(a.college_roll).localeCompare(String(b.college_roll));
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
    const cfg = GROUP_CONFIGS[state.activeGroup] || GROUP_CONFIGS.science;
    const filtered = state.filteredStudents;
    const totalItems = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / state.pageSize));
    const startIdx = (state.currentPage - 1) * state.pageSize;
    const endIdx = Math.min(startIdx + state.pageSize, totalItems);
    const pageSlice = filtered.slice(startIdx, endIdx);

    const isSectionFiltered = state.sectionFilter !== "ALL";

    if (state.sortBy === "total_marks" || state.sortBy === "gpa") {
      els.rankColHeader.textContent = isSectionFiltered
        ? `Sec ${state.sectionFilter} Rank`
        : "Rank";
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
        ? `Showing ${startIdx + 1}–${endIdx} of ${totalItems} ${cfg.label} student${
            totalItems === 1 ? "" : "s"
          }${secSuffix}`
        : `No students found in ${cfg.label}${secSuffix}`;

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
        if (state.sortBy === "total_marks" || state.sortBy === "gpa") {
          rankNum = isSectionFiltered
            ? s.section_marks_rank || s.serial_no
            : s.marks_rank || s.serial_no;
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

        const hasMarks = s.total_marks > 0;
        let rankBadgeClass = "rank-badge";
        if (hasMarks && rankNum === 1) rankBadgeClass += " top-1";
        else if (hasMarks && rankNum === 2) rankBadgeClass += " top-2";
        else if (hasMarks && rankNum === 3) rankBadgeClass += " top-3";

        const rankLabel =
          hasMarks && typeof rankNum === "number"
            ? `#${rankNum}`
            : `${s.serial_no}`;

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
        } else if (s.status === "pending") {
          gpaHtml = `<span class="gpa-pill">Pending</span>`;
        }

        const totalDisplay =
          s.total_marks > 0
            ? `<span class="metric-primary">${s.total_marks}</span><span class="metric-sub">/ 1300</span>`
            : `<span class="metric-sub">${
                s.status === "pending" ? "Scraping…" : "No marksheet"
              }</span>`;

        let secondMetricDisplay = `<span class="metric-sub">—</span>`;
        let mobileMetricLabel = cfg.hasPcm ? "PCM %:" : "SCORE %:";

        if (cfg.hasPcm) {
          if (s.pcm_marks > 0) {
            secondMetricDisplay = `<span class="metric-primary">${s.pcm_percentile.toFixed(
              2
            )}%</span><span class="metric-sub">${s.pcm_marks} / 600</span>`;
          }
        } else {
          if (s.total_marks > 0) {
            const pct = ((s.total_marks / 1300) * 100).toFixed(2);
            secondMetricDisplay = `<span class="metric-primary">${pct}%</span><span class="metric-sub">Overall Score</span>`;
          } else if (Array.isArray(s.subjects) && s.subjects.length > 0) {
            mobileMetricLabel = "SUBJECTS:";
            secondMetricDisplay = `<span class="metric-primary">${s.subjects.length} Subj</span><span class="metric-sub">Registered</span>`;
          }
        }

        const groupShortPrefix =
          state.activeGroup === "all"
            ? `${
                s.group_key === "humanities"
                  ? "Hum • "
                  : s.group_key === "business_studies"
                  ? "Bus • "
                  : "Sci • "
              }`
            : "";

        return `<tr data-roll="${escapeHtml(
          s.college_roll
        )}" tabindex="0" role="button" aria-label="View marksheet for ${escapeHtml(
          s.name
        )}, College Roll ${escapeHtml(s.college_roll)}, Section ${escapeHtml(
          s.section
        )}">
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
          <td class="center-col cell-sec"><span class="sec-badge">${escapeHtml(
            groupShortPrefix
          )}Sec ${escapeHtml(s.section)}</span></td>
          <td class="center-col cell-gpa">${gpaHtml}</td>
          <td class="num-col cell-marks">${totalDisplay}</td>
          <td class="num-col cell-pcm" data-mobile-label="${escapeHtml(
            mobileMetricLabel
          )}">${secondMetricDisplay}</td>
          <td class="num-col hide-tablet cell-action no-print">
            <span class="view-link">${
              s.total_marks > 0 ? "Marksheet" : "Profile"
            } &rarr;</span>
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
    const isScience =
      student.group_key === "science" ||
      String(student.group || "").toUpperCase() === "SCIENCE";

    const overallPercentage =
      student.total_marks > 0
        ? ((student.total_marks / 1300) * 100).toFixed(2)
        : "0.00";

    const gpaDisplay = student.gpa
      ? student.gpa
      : student.result === "A"
      ? "Absent"
      : student.status === "pending"
      ? "Pending"
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
        : student.status === "pending"
        ? "Marksheet Scraping in Progress"
        : "Record Unavailable";

    let subjectsRowsHtml = "";
    if (Array.isArray(student.subjects) && student.subjects.length > 0) {
      subjectsRowsHtml = student.subjects
        .map((sub) => {
          const pct =
            sub.marks > 0 && sub.max_marks
              ? `${((sub.marks / sub.max_marks) * 100).toFixed(1)}%`
              : "—";
          const typeTag = sub.is_pcm
            ? `<span class="pcm-tag">PCM</span>`
            : sub.subject_type
            ? `<span class="pcm-tag">${escapeHtml(sub.subject_type)}</span>`
            : "";

          const marksCellText =
            sub.marks > 0
              ? `${escapeHtml(sub.marks_display || sub.marks)} <span style="color: var(--text-muted); font-weight: 400; font-size: 0.76rem;">/ ${
                  sub.max_marks
                }</span>`
              : `<span style="color: var(--text-muted); font-weight: 400;">${escapeHtml(
                  sub.marks_display || "—"
                )} (${sub.max_marks})</span>`;

          return `<tr class="${sub.is_pcm ? "pcm-row" : ""}">
            <td style="font-family: var(--font-mono); font-size: 0.81rem; color: var(--text-secondary);">
              ${escapeHtml(sub.code)}
            </td>
            <td style="font-weight: 500;">
              ${escapeHtml(sub.subject)} ${typeTag}
            </td>
            <td class="center-col">
              <span class="gpa-pill ${
                sub.grade === "A+"
                  ? "gpa-max"
                  : sub.grade === "F"
                  ? "gpa-fail"
                  : ""
              }">${escapeHtml(sub.grade)}</span>
            </td>
            <td class="num-col" style="font-family: var(--font-mono); font-weight: 600;">
              ${marksCellText}
            </td>
            <td class="num-col hide-mobile" style="font-family: var(--font-mono); color: var(--text-secondary); font-size: 0.81rem;">
              ${pct}
            </td>
          </tr>`;
        })
        .join("");

      if (student.total_marks > 0) {
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
      }
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

    const thirdAndFourthMetricCards = isScience
      ? `
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
      `
      : `
        <div class="sheet-metric-box highlighted">
          <div class="sm-label">Overall Score %</div>
          <div class="sm-value">${
            student.total_marks > 0 ? `${overallPercentage}%` : "—"
          }</div>
          <div class="sm-sub">Across 1300 total marks</div>
        </div>
        <div class="sheet-metric-box">
          <div class="sm-label">Registered Subjects</div>
          <div class="sm-value">${
            Array.isArray(student.subjects) ? student.subjects.length : 7
          } Subjects</div>
          <div class="sm-sub">Academic Year ${escapeHtml(
            student.academic_year || "2"
          )} Examinee</div>
        </div>
      `;

    const bottomFormulaBox = isScience
      ? `
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
      `
      : `
      <div class="pcm-breakdown-card">
        <div>
          <div class="pcm-formula-title">Overall Score Calculation (${escapeHtml(
            student.group
          )} Division)</div>
          <div class="pcm-formula-desc">
            Total marks across 3 Compulsory subjects (500) + 3 Group Elective subjects (600) + 4th Subject (200) = 1300 maximum
          </div>
        </div>
        <div class="pcm-equation">
          ${student.total_marks || 0} &divide; 1300 &times; 100 = <strong>${overallPercentage}%</strong>
        </div>
      </div>
      `;

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
          <div class="id-item-value">Section ${escapeHtml(
            student.section || "A"
          )}</div>
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
            student.total_marks > 0 ? `${student.total_marks} / 1300` : "Pending"
          }</div>
          <div class="sm-sub">${escapeHtml(marksRankSub)}</div>
        </div>
        ${thirdAndFourthMetricCards}
      </div>

      <!-- Subject-wise Marksheet Table -->
      <div class="section-heading">
        <span>Subject-Wise ${
          student.total_marks > 0 ? "Marks Breakdown" : "Registered Subjects"
        }</span>
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

      ${bottomFormulaBox}

      <div class="sheet-footer">
        <span>Dhaka College HSC 2026 Official Result Transcript</span>
        <span>Identification by Student Name &amp; College Roll (${escapeHtml(
          student.college_roll
        )} &bull; ${escapeHtml(student.group)} &bull; Section ${escapeHtml(
      student.section
    )})</span>
      </div>
    `;

    const idx = state.filteredStudents.findIndex(
      (s) => String(s.college_roll) === String(student.college_roll)
    );
    els.prevStudentBtn.disabled = idx <= 0;
    els.nextStudentBtn.disabled =
      idx === -1 || idx >= state.filteredStudents.length - 1;
  }

  function openStudentMarksheet(roll, pushHistory = true, replaceHistory = false) {
    const student = state.byRollGlobal.get(String(roll));
    if (!student) {
      showDirectoryView(false);
      return;
    }

    // If the student belongs to a different group than the currently active one (and not in 'all'), switch group context
    if (
      state.activeGroup !== "all" &&
      student.group_key &&
      student.group_key !== state.activeGroup
    ) {
      activateGroup(student.group_key, true);
    }

    if (state.activeView === "directory") {
      state.savedScrollY =
        window.scrollY || document.documentElement.scrollTop || 0;
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
        { view: "marksheet", roll: student.college_roll, group: state.activeGroup },
        "",
        targetHash
      );
      state.pushedMarksheetHistory = true;
    } else if (replaceHistory) {
      history.replaceState(
        { view: "marksheet", roll: student.college_roll, group: state.activeGroup },
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

    const cfg = GROUP_CONFIGS[state.activeGroup] || GROUP_CONFIGS.science;
    document.title = `Dhaka College HSC 2026 — ${cfg.label} Results & Rankings`;

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
      const targetHash =
        state.activeGroup !== "science" ? `#group=${state.activeGroup}` : "";
      history.replaceState(
        { view: "directory", group: state.activeGroup },
        "",
        window.location.pathname + window.location.search + targetHash
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
      state.currentPage = Math.floor(nextIdx / state.pageSize) + 1;
      renderTableCurrentPage();
      openStudentMarksheet(nextStudent.college_roll, false, true);
    }
  }

  function parseUrlHash() {
    const hash = window.location.hash || "";
    const rollMatch = hash.match(/roll=([^&]+)/);
    const groupMatch = hash.match(/group=([^&]+)/);
    return {
      roll: rollMatch ? decodeURIComponent(rollMatch[1]) : null,
      group: groupMatch ? decodeURIComponent(groupMatch[1]) : null,
    };
  }

  function bindEvents() {
    els.pageSizeSelect.value = String(state.pageSize);

    // Academic Group / Division Tabs
    els.groupTabsContainer.addEventListener("click", async (e) => {
      const tab = e.target.closest(".group-tab[data-group]");
      if (!tab) return;
      const gKey = tab.getAttribute("data-group");
      if (!gKey || state.activeGroup === gKey) return;

      await activateGroup(gKey, true);
      const targetHash = gKey !== "science" ? `#group=${gKey}` : "";
      history.replaceState(
        { view: "directory", group: gKey },
        "",
        window.location.pathname + window.location.search + targetHash
      );
    });

    // Section Filter Pills
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
        await loadInitialData(true);
        rebuildGlobalRollMap();
        updateGroupTabBadges();
        await activateGroup(state.activeGroup, false);
        if (state.activeView === "marksheet" && state.currentRoll) {
          const updated = state.byRollGlobal.get(state.currentRoll);
          if (updated) renderMarksheet(updated);
        }
      } catch (_err) {
        els.cacheStatusText.textContent = "Sync failed";
      } finally {
        els.refreshCacheBtn.disabled = false;
      }
    });

    // Browser / Android Hardware Back Button via popstate
    window.addEventListener("popstate", (e) => {
      const parsed = parseUrlHash();
      const rollFromState =
        e.state && e.state.view === "marksheet" ? e.state.roll : null;
      const targetRoll = rollFromState || parsed.roll;

      if (targetRoll && state.byRollGlobal.has(String(targetRoll))) {
        openStudentMarksheet(targetRoll, false, false);
      } else {
        if (parsed.group && GROUP_CONFIGS[parsed.group]) {
          activateGroup(parsed.group, false);
        }
        state.pushedMarksheetHistory = false;
        showDirectoryView(true);
      }
    });

    // Keyboard shortcuts inside marksheet view
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
      await loadInitialData(false);
      rebuildGlobalRollMap();
      updateGroupTabBadges();

      const parsedHash = parseUrlHash();
      const initialGroup =
        parsedHash.group && GROUP_CONFIGS[parsedHash.group]
          ? parsedHash.group
          : parsedHash.roll
          ? detectGroupKeyFromRoll(parsedHash.roll, "science")
          : "science";

      await activateGroup(initialGroup, true);

      if (parsedHash.roll && state.byRollGlobal.has(String(parsedHash.roll))) {
        history.replaceState(
          { view: "directory", group: initialGroup },
          "",
          window.location.pathname + window.location.search
        );
        openStudentMarksheet(parsedHash.roll, true, false);
      } else {
        showDirectoryView(false);
      }
    } catch (err) {
      els.loadingSubText.textContent =
        err && err.message ? err.message : "Failed to load JSON data.";
    }
  }

  init();
})();
