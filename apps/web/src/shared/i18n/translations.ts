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
    card2Badge: string;
    card2Title: string;
    card2Desc: string;
    card3Badge: string;
    card3Title: string;
    card3Desc: string;
    card4Badge: string;
    card4Title: string;
    card4Desc: string;
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
      sdlc: "SDLC Board",
      office: "Office OS",
      deliberations: "Deliberations",
      signIn: "Sign In",
      launchConsole: "Console",
    },
    hero: {
      badge: "Sovereign AI Engineering Rig & Operating System",
      titleStart: "The Autonomous AI",
      titleHighlight: "Engineering Organization",
      titleEnd: "Platform",
      subtitle:
        "Pairs an invariant Rust-based Office OS with the 16-stage canonical SDLC. Orchestrate specialized AI employees, conduct formal consensus meetings, and deliver software under absolute human founder sovereignty.",
      ctaPrimary: "Access Command Center",
      ctaSecondary: "Explore Platform",
      trust: {
        rustEngine: "Invariant Rust Core",
        stageGates: "16 Cryptographic Gates",
        traceability: "Full Knowledge Graph",
      },
      telemetry: {
        activeAgents: "Active Agents",
        sdlcGates: "SDLC Gates Passed",
        routingLatency: "Routing Latency",
        securityStatus: "Security Policy",
        enforced: "Enforced",
      },
    },
    showcase: {
      badge: "Interactive Command Center",
      title: "Engineered for Complete Operational Visibility",
      subtitle: "Switch between core platform surfaces to observe sovereign multi-agent coordination.",
      tabSdlc: "SDLC Pipeline",
      tabOffice: "Office OS",
      tabDeliberations: "Deliberation Rooms",
      tabKnowledge: "Knowledge Graph",
      sdlc: {
        title: "Canonical 16-Stage Deterministic SDLC",
        desc: "Strictly gates work transitions from requirements to verification with SHA-256 baseline verification.",
        item1Code: "[RE]",
        item1Name: "Requirements Engineering",
        item1Status: "Gate Passed",
        item2Code: "[SA]",
        item2Name: "System Architecture",
        item2Status: "Gate Passed",
        item3Code: "[DV]",
        item3Name: "Development Engineering",
        item3Status: "Active Run",
        item4Code: "[TE]",
        item4Name: "Test & Verification",
        item4Status: "Queued",
        footerText: "16-stage pipeline guarantees verifiable software delivery with human oversight.",
      },
      office: {
        title: "Persistent AI Workforce & Organizational Hierarchy",
        desc: "Decouples persistent employee identities and roles from ephemeral LLM inference runs.",
        role1: "CEO / AI #001",
        role1Desc: "Executive orchestration, resource allocation, and project charter baselining.",
        role2: "Architecture Lead",
        role2Desc: "Boundary definitions, component interfaces, and technical governance.",
        role3: "Engineering Specialist",
        role3Desc: "Domain-specific code authoring, automated refactoring, and test suite execution.",
        footerText: "Structured organizational charts enforce clear reporting lines and RBAC scopes.",
      },
      deliberations: {
        title: "Formal Deliberation & Voting Rooms",
        desc: "Real-time meeting transcripts, speaker queueing, and cryptographic resolution recording.",
        quorum: "Quorum Met: 4 / 4 Votes",
        consensus: "Consensus: Unanimous Approval",
        transcriptFeed: "Live WebSocket Transcript Stream (Sub-second event propagation)",
        footerText: "Decisions become immutable nodes in the permanent organizational knowledge graph.",
      },
      knowledge: {
        title: "Epistemic Hybrid Knowledge & Traceability",
        desc: "Unifies dense vector embeddings with Apache AGE graph traversals for total traceability.",
        hybridSearch: "Dense Vector (bge-small) + Exact Lexical Match",
        graphLinks: "Direct Graph Traversal: Intent -> Decision -> Artifact -> Test",
        footerText: "Query requirements, architectural decisions, and source code relationships in real-time.",
      },
    },
    bento: {
      badge: "Core Architecture",
      title: "Built on Sovereign Architectural Pillars",
      subtitle: "A modern foundation designed to run on your own infrastructure with zero third-party lock-in.",
      card1Badge: "Tier 1-4 Model",
      card1Title: "Four-Tier Organizational Hierarchy",
      card1Desc: "From the Human Founder down to Executive, Operational, and Specialist AI agents, every role operates within strictly delegated policy boundaries.",
      card2Badge: "Zero Drift",
      card2Title: "Cryptographic Stage Invariance",
      card2Desc: "Stage gates require explicit cryptographic SHA-256 baselines before artifacts can progress down the pipeline.",
      card3Badge: "Sub-15ms Latency",
      card3Title: "Rust High-Performance Event Bus",
      card3Desc: "Axum and Tower micro-services ensure high-throughput WebSocket message propagation between AI agents.",
      card4Badge: "Enterprise Ready",
      card4Title: "Universal OpenID Connect IAM",
      card4Desc: "Native OAuth 2.1 / OIDC Core 1.0 with PKCE support for Rauthy, Keycloak, and Authentik driven by dynamic runtime config.",
    },
    workflow: {
      badge: "Autonomous Execution",
      title: "How avrig Coordinates Engineering",
      subtitle: "A repeatable, predictable engineering sequence that bridges human strategy with autonomous delivery.",
      step1Num: "01",
      step1Title: "Founder Intent & Charter",
      step1Desc: "Founder issues high-level goals. The CEO agent generates the project charter and resource allocations.",
      step2Num: "02",
      step2Title: "Deliberation & Consensus",
      step2Desc: "Department Heads assemble in deliberation rooms to debate tradeoffs and formalize technical designs.",
      step3Num: "03",
      step3Title: "16-Stage SDLC Pipeline",
      step3Desc: "Work items advance through invariant stages with automated validation, static analysis, and unit test execution.",
      step4Num: "04",
      step4Title: "Founder Verification & Release",
      step4Desc: "Founder inspects final verifiable baselines and authorizes release with ultimate sovereign sign-off.",
    },
    ctaBanner: {
      badge: "Command Your Autonomous Organization",
      title: "Ready to Experience the Sovereign AI Engineering Rig?",
      subtitle: "Launch the browser Command Center to inspect active AI agents, monitor SDLC boards, and govern deliberations.",
      buttonPrimary: "Launch Command Center",
      buttonSecondary: "Enter Operator Preview",
    },
    hierarchy: {
      title: "Four-Tier Organizational Hierarchy",
      subtitle: "Decoupled persistent employee identity from ephemeral LLM execution runtimes.",
      founder: "Human Founder",
      founderRole: "Ultimate Authority & Final Sign-Off",
      ceo: "CEO / AI #001",
      ceoRole: "Operations, Resource Allocation & Project Charter",
      deptHeads: "Department Heads",
      deptHeadsRole: "Architecture, Engineering, Security & Product",
      specialists: "Specialist Agents",
      specialistsRole: "Autonomous Execution Across 16 SDLC Stages",
    },
    features: {
      sectionTitle: "Built for Autonomous Engineering Governance",
      sectionSubtitle: "Structured models are authoritative; visualizations are representations.",
      sdlcTitle: "16-Stage Invariant SDLC",
      sdlcDesc:
        "Cryptographically signed stage gates from Business Intent through Architecture, Coding, Verification, and optional Deployment.",
      officeTitle: "Rust Office Operating System",
      officeDesc:
        "Persistent AI employee identities, departmental org chart reporting lines, and granular policy boundaries.",
      deliberationsTitle: "Meeting Deliberation Rooms",
      deliberationsDesc:
        "Real-time speaker turns, live speech transcript streaming over WebSocket, and formal resolution voting.",
      oidcTitle: "Universal Enterprise IAM",
      oidcDesc:
        "Seamless OpenID Connect Core 1.0 with PKCE supporting Rauthy, Keycloak, and Authentik driven by runtime config.",
    },
    login: {
      title: "avrig Command Center",
      subtitle: "Autonomous organizational operations require authorized founder or operator authentication.",
      authorityConnected: "Configured Authority",
      ssoButton: "Sign In via Universal OIDC",
      connecting: "Connecting to IdP...",
      demoButton: "Enter Operator Preview",
      demoNote: "Explore the live command center UI without signing in.",
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
      sdlc: "Papan SDLC",
      office: "OS Kantor",
      deliberations: "Musyawarah",
      signIn: "Masuk",
      launchConsole: "Konsol",
    },
    hero: {
      badge: "Harness Rekayasa AI Berdaulat & Sistem Operasi Organisasi",
      titleStart: "Platform Organisasi",
      titleHighlight: "Rekayasa AI Otonom",
      titleEnd: "Berdaulat",
      subtitle:
        "Memadukan OS Kantor berbasis Rust dengan 16 tahap SDLC kanonikal. Kelola staf AI spesialis, jalankan rapat musyawarah mufakat, dan bangun perangkat lunak di bawah kedaulatan mutlak Founder manusia.",
      ctaPrimary: "Buka Pusat Komando",
      ctaSecondary: "Pelajari Platform",
      trust: {
        rustEngine: "Mesin Inti Rust Invarian",
        stageGates: "16 Gerbang Kriptografis",
        traceability: "Graf Pengetahuan Lengkap",
      },
      telemetry: {
        activeAgents: "Agen Aktif",
        sdlcGates: "Gerbang SDLC Lolos",
        routingLatency: "Latensi Routing",
        securityStatus: "Kebijakan Keamanan",
        enforced: "Ditegakkan",
      },
    },
    showcase: {
      badge: "Pusat Komando Interaktif",
      title: "Dirancang untuk Visibilitas Operasional Menyeluruh",
      subtitle: "Pilih modul utama di bawah ini untuk melihat orkestrasi multi-agen berdaulat secara langsung.",
      tabSdlc: "Pipeline SDLC",
      tabOffice: "OS Kantor",
      tabDeliberations: "Ruang Musyawarah",
      tabKnowledge: "Graf Pengetahuan",
      sdlc: {
        title: "16 Tahap SDLC Deterministik Kanonikal",
        desc: "Mengontrol transisi pekerjaan dari kebutuhan hingga verifikasi dengan validasi hash SHA-256.",
        item1Code: "[RE]",
        item1Name: "Rekayasa Kebutuhan",
        item1Status: "Gerbang Lolos",
        item2Code: "[SA]",
        item2Name: "Arsitektur Sistem",
        item2Status: "Gerbang Lolos",
        item3Code: "[DV]",
        item3Name: "Rekayasa Pengkodean",
        item3Status: "Sedang Berjalan",
        item4Code: "[TE]",
        item4Name: "Pengujian & Verifikasi",
        item4Status: "Dalam Antrean",
        footerText: "Pipeline 16 tahap menjamin pengiriman perangkat lunak yang terverifikasi di bawah pengawasan manusia.",
      },
      office: {
        title: "Tenaga Kerja AI Persisten & Hierarki Organisasi",
        desc: "Memisahkan identitas staf AI yang persisten dari eksekusi inferensi model LLM yang bersifat sementara.",
        role1: "CEO / AI #001",
        role1Desc: "Orkestrasi eksekutif, alokasi sumber daya, dan penetapan piagam proyek.",
        role2: "Kepala Arsitektur",
        role2Desc: "Definisi batas sistem, kontrak antarmuka komponen, dan tata kelola teknis.",
        role3: "Spesialis Rekayasa",
        role3Desc: "Penulisan kode domain, refactoring otomatis, dan eksekusi pengujian.",
        footerText: "Struktur organisasi formal menegakkan garis pelaporan dan cakupan RBAC yang jelas.",
      },
      deliberations: {
        title: "Ruang Musyawarah & Pemungutan Suara",
        desc: "Transkrip rapat real-time, antrean bicara teratur, dan pencatatan resolusi kriptografis.",
        quorum: "Kuorum Terpenuhi: 4 / 4 Suara",
        consensus: "Konsensus: Disetujui Bulat",
        transcriptFeed: "Aliran Transkrip WebSocket Langsung (Propagasi pesan sub-detik)",
        footerText: "Setiap keputusan menjadi simpul abadi dalam graf pengetahuan organisasi.",
      },
      knowledge: {
        title: "Pengetahuan Epistemik Hibrida & Keterlacakan",
        desc: "Menggabungkan pencarian vektor dengan penelusuran graf Apache AGE untuk keterlacakan total.",
        hybridSearch: "Vektor Padat (bge-small) + Pencocokan Leksikal Tepat",
        graphLinks: "Penelusuran Graf Langsung: Niat -> Keputusan -> Kode -> Uji",
        footerText: "Kueri relasi kebutuhan, keputusan arsitektur, dan artefak kode secara instan.",
      },
    },
    bento: {
      badge: "Arsitektur Utama",
      title: "Dibangun di Atas Pilar Arsitektur Berdaulat",
      subtitle: "Fondasi modern yang dirancang untuk berjalan di infrastruktur mandiri tanpa ketergantungan pihak ketiga.",
      card1Badge: "Model 4 Tingkat",
      card1Title: "Hierarki Organisasi Empat Tingkat",
      card1Desc: "Dari Founder manusia hingga agen Eksekutif, Operasional, dan Spesialis, setiap peran berjalan dalam batas kebijakan yang didelegasikan secara ketat.",
      card2Badge: "Nol Deviasi",
      card2Title: "Invarian Tahap Kriptografis",
      card2Desc: "Setiap gerbang tahap memerlukan verifikasi hash SHA-256 eksplisit sebelum artefak dapat melangkah ke tahap berikutnya.",
      card3Badge: "Latensi < 15ms",
      card3Title: "Bus Peristiwa Kinerja Tinggi Rust",
      card3Desc: "Layanan mikro berbasis Axum dan Tower memastikan propagasi pesan WebSocket berkecepatan tinggi antar agen AI.",
      card4Badge: "Siap Perusahaan",
      card4Title: "IAM OpenID Connect Universal",
      card4Desc: "Dukungan OAuth 2.1 / OIDC Core 1.0 dengan PKCE untuk Rauthy, Keycloak, dan Authentik yang dipandu konfigurasi runtime dinamis.",
    },
    workflow: {
      badge: "Eksekusi Otonom",
      title: "Cara avrig Mengoordinasikan Rekayasa",
      subtitle: "Alur kerja berulang dan terstruktur yang menjembatani strategi manusia dengan eksekusi otonom.",
      step1Num: "01",
      step1Title: "Niat Founder & Piagam",
      step1Desc: "Founder memberikan arahan strategis. Agen CEO menyusun piagam proyek dan pembagian sumber daya.",
      step2Num: "02",
      step2Title: "Musyawarah & Mufakat",
      step2Desc: "Kepala Departemen berkumpul di ruang musyawarah untuk mendiskusikan opsi dan memformalkan desain arsitektur.",
      step3Num: "03",
      step3Title: "Pipeline 16 Tahap SDLC",
      step3Desc: "Item pekerjaan bergerak melalui tahap invarian dengan validasi otomatis, analisis statis, dan eksekusi pengujian.",
      step4Num: "04",
      step4Title: "Verifikasi Founder & Rilis",
      step4Desc: "Founder meninjau artefak final yang terverifikasi dan memberikan persetujuan rilis berdaulat mutlak.",
    },
    ctaBanner: {
      badge: "Kendalikan Organisasi Otonom Anda",
      title: "Siap Menjalankan Rig Rekayasa AI Berdaulat?",
      subtitle: "Buka Pusat Komando peramban untuk memantau agen AI aktif, meninjau papan SDLC, dan mengelola musyawarah.",
      buttonPrimary: "Buka Pusat Komando",
      buttonSecondary: "Masuk Mode Pratinjau",
    },
    hierarchy: {
      title: "Hierarki Organisasi Empat Tingkat",
      subtitle: "Memisahkan identitas staf AI persisten dari runtime eksekusi LLM yang efemeral.",
      founder: "Founder Manusia",
      founderRole: "Otoritas Tertinggi & Persetujuan Akhir",
      ceo: "CEO / AI #001",
      ceoRole: "Operasional, Alokasi Sumber Daya & Piagam Proyek",
      deptHeads: "Kepala Departemen",
      deptHeadsRole: "Arsitektur, Rekayasa, Keamanan & Produk",
      specialists: "Agen Spesialis",
      specialistsRole: "Eksekusi Otonom di 16 Tahap SDLC Kanonikal",
    },
    features: {
      sectionTitle: "Dirancang untuk Tata Kelola Rekayasa Otonom",
      sectionSubtitle: "Model terstruktur adalah sumber kebenaran; visualisasi adalah representasi.",
      sdlcTitle: "16 Tahap SDLC Invarian",
      sdlcDesc:
        "Gerbang tahap bertanda tangan kriptografis dari Niat Bisnis, Desain Arsitektur, Pengkodean, Pengujian, hingga Rilis.",
      officeTitle: "OS Kantor Berbasis Rust",
      officeDesc:
        "Identitas staf AI yang persisten, struktur departemen organisasi, dan batas kebijakan otorisasi yang ketat.",
      deliberationsTitle: "Ruang Musyawarah Rapat",
      deliberationsDesc:
        "Antrean giliran bicara waktu-nyata, transkrip percakapan langsung via WebSocket, dan pemungutan suara resolusi.",
      oidcTitle: "IAM Perusahaan Universal",
      oidcDesc:
        "Dukungan OpenID Connect Core 1.0 dengan PKCE untuk Rauthy, Keycloak, dan Authentik melalui konfigurasi runtime.",
    },
    login: {
      title: "Pusat Komando avrig",
      subtitle: "Operasi organisasi otonom membutuhkan autentikasi resmi Founder atau operator berwenang.",
      authorityConnected: "Otoritas Terhubung",
      ssoButton: "Masuk via Universal OIDC",
      connecting: "Menghubungkan ke IdP...",
      demoButton: "Masuk Mode Pratinjau Operator",
      demoNote: "Jelajahi antarmuka Pusat Komando langsung tanpa login akun.",
      close: "Batal",
    },
    theme: {
      dark: "Gelap",
      light: "Terang",
      system: "Sistem Komputer",
    },
  },
};
