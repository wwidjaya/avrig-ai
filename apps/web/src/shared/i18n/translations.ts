export type Locale = "en" | "id";

export interface Translations {
  nav: {
    architecture: string;
    sdlc: string;
    office: string;
    deliberations: string;
    signIn: string;
    launchConsole: string;
  };
  hero: {
    badge: string;
    titleStart: string;
    titleHighlight: string;
    titleEnd: string;
    subtitle: string;
    ctaPrimary: string;
    ctaSecondary: string;
    trust: {
      rustEngine: string;
      stageGates: string;
      traceability: string;
    };
    telemetry: {
      activeAgents: string;
      sdlcGates: string;
      routingLatency: string;
      securityStatus: string;
      enforced: string;
    };
  };
  certificate: {
    inspect: string;
    stageOf: string;
    version: string;
    pin: string;
    reCheck1: string;
    reCheck2: string;
    saCheck1: string;
    saCheck2: string;
    dvCheck1: string;
    dvCheck2: string;
    teCheck1: string;
    teCheck2: string;
    approvalGiven: string;
    approvalPending: string;
  };
  showcase: {
    badge: string;
    title: string;
    subtitle: string;
    tabSdlc: string;
    tabOffice: string;
    tabDeliberations: string;
    tabKnowledge: string;
    sdlc: {
      title: string;
      desc: string;
      item1Code: string;
      item1Name: string;
      item1Status: string;
      item2Code: string;
      item2Name: string;
      item2Status: string;
      item3Code: string;
      item3Name: string;
      item3Status: string;
      item4Code: string;
      item4Name: string;
      item4Status: string;
      footerText: string;
    };
    office: {
      title: string;
      desc: string;
      tier1: string;
      tier2: string;
      tier3: string;
      role1: string;
      role1Desc: string;
      role2: string;
      role2Desc: string;
      role3: string;
      role3Desc: string;
      footerText: string;
    };
    deliberations: {
      title: string;
      desc: string;
      quorum: string;
      consensus: string;
      transcriptFeed: string;
      footerText: string;
    };
    knowledge: {
      title: string;
      desc: string;
      hybridSearch: string;
      graphLinks: string;
      footerText: string;
    };
  };
  bento: {
    badge: string;
    title: string;
    subtitle: string;
    card1Badge: string;
    card1Title: string;
    card1Desc: string;
    card1Footer: string;
    card2Badge: string;
    card2Title: string;
    card2Desc: string;
    card2Footer: string;
    card3Badge: string;
    card3Title: string;
    card3Desc: string;
    card3Footer: string;
    card4Badge: string;
    card4Title: string;
    card4Desc: string;
    card4Footer: string;
  };
  workflow: {
    badge: string;
    title: string;
    subtitle: string;
    step1Num: string;
    step1Title: string;
    step1Desc: string;
    step2Num: string;
    step2Title: string;
    step2Desc: string;
    step3Num: string;
    step3Title: string;
    step3Desc: string;
    step4Num: string;
    step4Title: string;
    step4Desc: string;
  };
  ctaBanner: {
    badge: string;
    title: string;
    subtitle: string;
    buttonPrimary: string;
    buttonSecondary: string;
  };
  hierarchy: {
    title: string;
    subtitle: string;
    founder: string;
    founderRole: string;
    ceo: string;
    ceoRole: string;
    deptHeads: string;
    deptHeadsRole: string;
    specialists: string;
    specialistsRole: string;
  };
  features: {
    sectionTitle: string;
    sectionSubtitle: string;
    sdlcTitle: string;
    sdlcDesc: string;
    officeTitle: string;
    officeDesc: string;
    deliberationsTitle: string;
    deliberationsDesc: string;
    oidcTitle: string;
    oidcDesc: string;
  };
  login: {
    title: string;
    subtitle: string;
    authorityConnected: string;
    ssoButton: string;
    connecting: string;
    demoButton: string;
    demoNote: string;
    close: string;
  };
  theme: {
    dark: string;
    light: string;
    system: string;
  };
}

export const translations: Record<Locale, Translations> = {
  en: {
    nav: {
      architecture: "Architecture",
      sdlc: "Stages",
      office: "Office",
      deliberations: "Deliberations",
      signIn: "Sign in",
      launchConsole: "Open console",
    },
    hero: {
      badge: "Software delivery, run as a company",
      titleStart: "Software delivery with",
      titleHighlight: "a signature",
      titleEnd: "at every stage",
      subtitle:
        "Agents plan, execute and verify each stage in a fixed order. Every stage leaves an artifact with a version pin, and only the founder can approve it.",
      ctaPrimary: "Open console",
      ctaSecondary: "See the stages",
      trust: {
        rustEngine: "Rust runtime",
        stageGates: "16 stages, fixed order",
        traceability: "Version pin on every artifact",
      },
      telemetry: {
        activeAgents: "Stages in the pipeline",
        sdlcGates: "Approvers",
        routingLatency: "Agent approvals permitted",
        securityStatus: "Version pin per artifact",
        enforced: "Always",
      },
    },
    certificate: {
      inspect: "Inspect stage",
      stageOf: "of 16",
      version: "Version",
      pin: "Pin",
      reCheck1: "12 user stories mapped",
      reCheck2: "0 unmapped requirements",
      saCheck1: "Topology contracts defined",
      saCheck2: "Schema and role boundaries locked",
      dvCheck1: "Clippy clean across the workspace",
      dvCheck2: "Commits signed by the agent",
      teCheck1: "48 cases in the suite",
      teCheck2: "OIDC assertion checked",
      approvalGiven: "Signed by the founder",
      approvalPending: "Awaiting founder approval",
    },
    showcase: {
      badge: "The console",
      title: "Every stage, artifact and decision in one record",
      subtitle:
        "Four views of the same record: the stage board, the office, the deliberation rooms and the knowledge graph.",
      tabSdlc: "Stages",
      tabOffice: "Office",
      tabDeliberations: "Rooms",
      tabKnowledge: "Knowledge",
      sdlc: {
        title: "A fixed sequence of sixteen stages",
        desc: "Each stage has an entry condition, a checklist and an artifact. Work moves on only when the artifact for that stage is accepted.",
        item1Code: "[RE]",
        item1Name: "Requirements engineering",
        item1Status: "Passed",
        item2Code: "[SA]",
        item2Name: "System architecture",
        item2Status: "Passed",
        item3Code: "[DV]",
        item3Name: "Development engineering",
        item3Status: "In progress",
        item4Code: "[TE]",
        item4Name: "Test and verification",
        item4Status: "Queued",
        footerText:
          "No stage skips its checklist, and no artifact moves forward without a version pin.",
      },
      office: {
        title: "Roles that persist between runs",
        desc: "An agent is an employee with a role and a reporting line. Identity persists across inference runs.",
        tier1: "Executive tier",
        tier2: "Operational tier",
        tier3: "Specialist tier",
        role1: "Chief executive",
        role1Desc: "Sets the project charter, allocates work and reports to the founder.",
        role2: "Architecture lead",
        role2Desc: "Defines module boundaries, interfaces and technical governance.",
        role3: "Engineering specialist",
        role3Desc: "Writes and reviews code inside one domain, and runs its tests.",
        footerText:
          "Every role works inside a delegated policy boundary, and none of them can approve a stage.",
      },
      deliberations: {
        title: "Deliberation rooms, on the record",
        desc: "Agents argue a decision in a chaired meeting. The resolution is written down and linked to the artifacts it changes.",
        quorum: "Quorum 4 of 4",
        consensus: "Resolved, unanimous",
        transcriptFeed: "The transcript streams as each speaker takes the floor",
        footerText:
          "A resolution becomes a link in the traceability record, not a message in a chat log.",
      },
      knowledge: {
        title: "Traceability from requirement to release",
        desc: "Every artifact is linked to the requirement it satisfies, the test that verifies it and the release it shipped in.",
        hybridSearch: "Dense vector search over decisions and artifacts",
        graphLinks: "Graph traversal: requirement, decision, artifact, test",
        footerText:
          "Ask why a line of code exists and get the requirement, the decision and the test behind it.",
      },
    },
    bento: {
      badge: "How it is built",
      title: "Four properties the system keeps",
      subtitle: "The parts that decide whether a claim can be trusted.",
      card1Badge: "Four tiers",
      card1Title: "The founder, then three tiers of agents",
      card1Desc:
        "The founder holds approval. Executives, operational leads and specialists work inside delegated boundaries, and every action is attributable to a role.",
      card1Footer: "Founder approval, delegated authority",
      card2Badge: "Version pins",
      card2Title: "An artifact is pinned to a version",
      card2Desc:
        "Each stage artifact carries a version, and every traceability link pins both of its ends, so a link is a statement about two versions rather than about artifacts in general.",
      card2Footer: "Version pins, immutable history",
      card3Badge: "One runtime",
      card3Title: "Office, board and rooms share an event bus",
      card3Desc:
        "The office, the stage board and the deliberation rooms publish and subscribe on the same Rust event bus, so a state change happens once and is read everywhere.",
      card3Footer: "Rust, Axum, one event bus",
      card4Badge: "OIDC",
      card4Title: "Any standards-compliant identity provider",
      card4Desc:
        "Discovery, PKCE and bearer tokens over plain OpenID Connect. Rauthy, Keycloak and Authentik work without a provider-specific SDK.",
      card4Footer: "Rauthy, Keycloak, Authentik",
    },
    workflow: {
      badge: "The sequence",
      title: "From founder intent to a signed release",
      subtitle: "Four movements, each one leaving something checkable behind.",
      step1Num: "01",
      step1Title: "Intent and charter",
      step1Desc:
        "The founder states the goal. The charter fixes scope, constraints and the acceptance criterion.",
      step2Num: "02",
      step2Title: "Design deliberation",
      step2Desc:
        "Leads argue the approach in a room with a chair, a quorum and a written resolution.",
      step3Num: "03",
      step3Title: "Stages in order",
      step3Desc:
        "Each of the sixteen stages runs its checklist and produces a versioned artifact before the next one starts.",
      step4Num: "04",
      step4Title: "Founder approval and release",
      step4Desc:
        "The founder reviews the pinned artifacts and signs. No agent can sign in their place.",
    },
    ctaBanner: {
      badge: "Open the console",
      title: "Read the record yourself",
      subtitle:
        "The console shows the stage board, the artifacts with their version pins, and what the founder signed.",
      buttonPrimary: "Open console",
      buttonSecondary: "Preview without signing in",
    },
    hierarchy: {
      title: "Four tiers of authority",
      subtitle: "Identity is decoupled from the runtime that does the work.",
      founder: "Human founder",
      founderRole: "Approval authority and final sign-off",
      ceo: "Chief executive",
      ceoRole: "Operations, allocation and the project charter",
      deptHeads: "Department heads",
      deptHeadsRole: "Architecture, engineering, security and product",
      specialists: "Specialist agents",
      specialistsRole: "Execution inside one stage and its checklist",
    },
    features: {
      sectionTitle: "Built for engineering under governance",
      sectionSubtitle: "The models are authoritative. The screens only represent them.",
      sdlcTitle: "Sixteen stages, fixed order",
      sdlcDesc:
        "Signed stage gates from business intent through architecture, coding and verification, to release.",
      officeTitle: "Rust office runtime",
      officeDesc: "Persistent employee identities, departmental reporting lines and policy boundaries.",
      deliberationsTitle: "Deliberation rooms",
      deliberationsDesc: "Spanning speaker turns, a streamed transcript and a formal resolution per meeting.",
      oidcTitle: "Universal OIDC",
      oidcDesc:
        "OpenID Connect with PKCE, driven by runtime configuration, against Rauthy, Keycloak or Authentik.",
    },
    login: {
      title: "Sign in to the console",
      subtitle: "Approval authority and the audit record attach to a signed-in operator.",
      authorityConnected: "Identity provider",
      ssoButton: "Sign in with OpenID Connect",
      connecting: "Redirecting to the identity provider",
      demoButton: "Preview without signing in",
      demoNote: "Opens the console without a session. Nothing is recorded against an operator.",
      close: "Cancel",
    },
    theme: {
      dark: "Dark",
      light: "Light",
      system: "System",
    },
  },
  id: {
    nav: {
      architecture: "Arsitektur",
      sdlc: "Tahapan",
      office: "Kantor",
      deliberations: "Musyawarah",
      signIn: "Masuk",
      launchConsole: "Buka konsol",
    },
    hero: {
      badge: "Pengiriman perangkat lunak, dikelola seperti perusahaan",
      titleStart: "Perangkat lunak",
      titleHighlight: "bertanda tangan",
      titleEnd: "di setiap tahap",
      subtitle:
        "Agen merencanakan, mengeksekusi dan memverifikasi setiap tahap dalam urutan tetap. Setiap tahap meninggalkan artefak dengan pin versi, dan hanya founder yang dapat menyetujuinya.",
      ctaPrimary: "Buka konsol",
      ctaSecondary: "Lihat tahapan",
      trust: {
        rustEngine: "Runtime Rust",
        stageGates: "16 tahap, urutan tetap",
        traceability: "Pin versi di setiap artefak",
      },
      telemetry: {
        activeAgents: "Tahap dalam pipeline",
        sdlcGates: "Pemberi persetujuan",
        routingLatency: "Persetujuan agen diizinkan",
        securityStatus: "Pin versi per artefak",
        enforced: "Selalu",
      },
    },
    certificate: {
      inspect: "Periksa tahap",
      stageOf: "dari 16",
      version: "Versi",
      pin: "Pin",
      reCheck1: "12 cerita pengguna terpetakan",
      reCheck2: "0 kebutuhan tanpa pemetaan",
      saCheck1: "Kontrak topologi terdefinisi",
      saCheck2: "Skema dan batas peran terkunci",
      dvCheck1: "Clippy bersih di seluruh workspace",
      dvCheck2: "Commit ditandatangani oleh agen",
      teCheck1: "48 kasus dalam rangkaian uji",
      teCheck2: "Asersi OIDC diperiksa",
      approvalGiven: "Ditandatangani founder",
      approvalPending: "Menunggu persetujuan founder",
    },
    showcase: {
      badge: "Konsol",
      title: "Setiap tahap, artefak dan keputusan dalam satu catatan",
      subtitle:
        "Empat tampilan dari catatan yang sama: papan tahap, kantor, ruang musyawarah dan graf pengetahuan.",
      tabSdlc: "Tahapan",
      tabOffice: "Kantor",
      tabDeliberations: "Ruang",
      tabKnowledge: "Pengetahuan",
      sdlc: {
        title: "Urutan tetap enam belas tahap",
        desc: "Setiap tahap punya syarat masuk, daftar periksa dan artefak. Pekerjaan berlanjut hanya setelah artefak tahap itu diterima.",
        item1Code: "[RE]",
        item1Name: "Rekayasa kebutuhan",
        item1Status: "Lolos",
        item2Code: "[SA]",
        item2Name: "Arsitektur sistem",
        item2Status: "Lolos",
        item3Code: "[DV]",
        item3Name: "Rekayasa pengembangan",
        item3Status: "Sedang berjalan",
        item4Code: "[TE]",
        item4Name: "Pengujian dan verifikasi",
        item4Status: "Dalam antrean",
        footerText:
          "Tidak ada tahap yang melewati daftar periksa, dan tidak ada artefak yang berlanjut tanpa pin versi.",
      },
      office: {
        title: "Peran yang bertahan antar proses",
        desc: "Agen adalah pegawai dengan peran dan garis pelaporan. Identitasnya bertahan antar proses inferensi.",
        tier1: "Tingkat 2, eksekutif",
        tier2: "Tingkat 3, operasional",
        tier3: "Tingkat 4, spesialis",
        role1: "Direktur utama",
        role1Desc: "Menyusun piagam proyek, membagi pekerjaan dan melapor kepada founder.",
        role2: "Kepala arsitektur",
        role2Desc: "Menetapkan batas modul, antarmuka dan tata kelola teknis.",
        role3: "Spesialis rekayasa",
        role3Desc: "Menulis dan meninjau kode dalam satu domain, lalu menjalankan pengujiannya.",
        footerText:
          "Setiap peran bekerja di dalam batas kebijakan yang didelegasikan, dan tidak satu pun dapat menyetujui tahap.",
      },
      deliberations: {
        title: "Ruang musyawarah, tercatat",
        desc: "Agen memperdebatkan keputusan dalam rapat yang dipimpin. Resolusi ditulis dan ditautkan ke artefak yang berubah.",
        quorum: "Kuorum 4 dari 4",
        consensus: "Diputuskan, bulat",
        transcriptFeed: "Transkrip mengalir saat setiap pembicara mengambil giliran",
        footerText:
          "Resolusi menjadi tautan dalam catatan keterlacakan, bukan pesan di riwayat obrolan.",
      },
      knowledge: {
        title: "Keterlacakan dari kebutuhan hingga rilis",
        desc: "Setiap artefak tertaut ke kebutuhan yang dipenuhinya, pengujian yang memverifikasinya dan rilis tempatnya dikirim.",
        hybridSearch: "Pencarian vektor padat atas keputusan dan artefak",
        graphLinks: "Penelusuran graf: kebutuhan, keputusan, artefak, uji",
        footerText:
          "Tanyakan alasan sebuah baris kode ada, dan dapatkan kebutuhan, keputusan serta uji di baliknya.",
      },
    },
    bento: {
      badge: "Cara sistem ini dibangun",
      title: "Empat sifat yang dijaga sistem",
      subtitle: "Bagian yang menentukan apakah sebuah klaim dapat dipercaya.",
      card1Badge: "Empat tingkat",
      card1Title: "Founder, lalu tiga tingkat agen",
      card1Desc:
        "Founder memegang persetujuan. Eksekutif, pimpinan operasional dan spesialis bekerja dalam batas yang didelegasikan, dan setiap tindakan dapat dilacak ke sebuah peran.",
      card1Footer: "Persetujuan founder, kewenangan didelegasikan",
      card2Badge: "Pin versi",
      card2Title: "Artefak dipin ke satu versi",
      card2Desc:
        "Setiap artefak tahap membawa versi, dan setiap tautan keterlacakan memin kedua ujungnya, sehingga tautan adalah pernyataan tentang dua versi tertentu.",
      card2Footer: "Pin versi, riwayat tak berubah",
      card3Badge: "Satu runtime",
      card3Title: "Kantor, papan dan ruang berbagi bus peristiwa",
      card3Desc:
        "Kantor, papan tahap dan ruang musyawarah menerbitkan dan berlangganan pada bus peristiwa Rust yang sama, sehingga satu perubahan dibaca di mana-mana.",
      card3Footer: "Rust, Axum, satu bus peristiwa",
      card4Badge: "OIDC",
      card4Title: "Penyedia identitas apa pun yang sesuai standar",
      card4Desc:
        "Discovery, PKCE dan token bearer lewat OpenID Connect biasa. Rauthy, Keycloak dan Authentik berjalan tanpa SDK khusus penyedia.",
      card4Footer: "Rauthy, Keycloak, Authentik",
    },
    workflow: {
      badge: "Urutannya",
      title: "Dari niat founder hingga rilis bertanda tangan",
      subtitle: "Empat langkah, masing-masing meninggalkan sesuatu yang dapat diperiksa.",
      step1Num: "01",
      step1Title: "Niat dan piagam",
      step1Desc:
        "Founder menyatakan tujuan. Piagam menetapkan lingkup, batasan dan kriteria penerimaan.",
      step2Num: "02",
      step2Title: "Musyawarah desain",
      step2Desc:
        "Para pimpinan memperdebatkan pendekatan dalam rapat dengan pemimpin, kuorum dan resolusi tertulis.",
      step3Num: "03",
      step3Title: "Tahapan berurutan",
      step3Desc:
        "Setiap dari enam belas tahap menjalankan daftar periksanya dan menghasilkan artefak berversi sebelum tahap berikutnya mulai.",
      step4Num: "04",
      step4Title: "Persetujuan founder dan rilis",
      step4Desc:
        "Founder meninjau artefak yang telah dipin dan menandatanganinya. Tidak ada agen yang dapat menandatangani menggantikannya.",
    },
    ctaBanner: {
      badge: "Buka konsol",
      title: "Baca catatannya sendiri",
      subtitle:
        "Konsol menampilkan papan tahap, artefak beserta pin versinya, dan apa yang ditandatangani founder.",
      buttonPrimary: "Buka konsol",
      buttonSecondary: "Pratinjau tanpa masuk",
    },
    hierarchy: {
      title: "Empat tingkat kewenangan",
      subtitle: "Identitas dipisahkan dari runtime yang menjalankan pekerjaan.",
      founder: "Founder manusia",
      founderRole: "Kewenangan persetujuan dan tanda tangan akhir",
      ceo: "Direktur utama",
      ceoRole: "Operasional, alokasi dan piagam proyek",
      deptHeads: "Kepala departemen",
      deptHeadsRole: "Arsitektur, rekayasa, keamanan dan produk",
      specialists: "Agen spesialis",
      specialistsRole: "Eksekusi dalam satu tahap dan daftar periksanya",
    },
    features: {
      sectionTitle: "Dibangun untuk rekayasa di bawah tata kelola",
      sectionSubtitle: "Model adalah acuan. Layar hanya merepresentasikannya.",
      sdlcTitle: "Enam belas tahap, urutan tetap",
      sdlcDesc:
        "Gerbang tahap bertanda tangan dari niat bisnis, arsitektur, pengkodean dan verifikasi, hingga rilis.",
      officeTitle: "Runtime kantor berbasis Rust",
      officeDesc: "Identitas pegawai yang bertahan, garis pelaporan departemen dan batas kebijakan.",
      deliberationsTitle: "Ruang musyawarah",
      deliberationsDesc: "Giliran bicara, transkrip yang dialirkan dan resolusi formal per rapat.",
      oidcTitle: "OIDC universal",
      oidcDesc:
        "OpenID Connect dengan PKCE, dipandu konfigurasi runtime, untuk Rauthy, Keycloak atau Authentik.",
    },
    login: {
      title: "Masuk ke konsol",
      subtitle: "Kewenangan persetujuan dan catatan audit melekat pada operator yang masuk.",
      authorityConnected: "Penyedia identitas",
      ssoButton: "Masuk dengan OpenID Connect",
      connecting: "Mengalihkan ke penyedia identitas",
      demoButton: "Pratinjau tanpa masuk",
      demoNote: "Membuka konsol tanpa sesi. Tidak ada yang dicatat atas nama operator.",
      close: "Batal",
    },
    theme: {
      dark: "Gelap",
      light: "Terang",
      system: "Sistem",
    },
  },
};
