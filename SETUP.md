# Oyen Math v4 (Autonomous Agentic AI Platform): Panduan Persediaan / Setup Guide

## A. Jalankan Sistem Secara Tempatan (5 Minit)
1. Buka terminal dalam folder `OyenMath`.
2. Pasang kebergantungan Python:
   ```bash
   pip install -r requirements.txt
   ```
   *(Kebergantungan utama: `langgraph>=1.0`, `anthropic>=0.40`, `sympy>=1.12`, `pydantic>=2.0`)*
3. Salin `.env.example` kepada `.env` dan isi `ANTHROPIC_API_KEY=` jika mahu menggunakan Claude LLM dan Claude Vision OCR.
   - **Tanpa kunci API (`ANTHROPIC_API_KEY` tidak ditetapkan):** Sistem Misi Pembelajaran Autonomi 12-nod (`agents/graph.py`) dan `/api/agent` tetap berjalan sepenuhnya menggunakan **mod peraturan deterministik (rule-based fallback)** dan pengesahan matematik **SymPy** (`agents/verification.py`).
4. Mulakan pelayan berbilang bebenang (`ThreadingHTTPServer`):
   ```bash
   python server.py
   ```
   Buka `http://localhost:8080` dalam pelayar (atau gunakan `PORT=9000 python server.py`).
5. Jalankan suite ujian automatik:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   node tests/test-suite.js
   ```

---

## B. Menggunakan Misi Pembelajaran Autonomi (`🤖 Misi Autonomi AI`)
1. Klik tab **🤖 Misi Autonomi AI** pada bar navigasi atas.
2. Pilih salah satu objektif prates (contoh: *"Kuasai Pembezaan sekurang-kurangnya 80%"* atau *"Ulang kaji prasyarat Hukum Indeks sebelum Pengamiran"*), tetapkan sasaran penguasaan (`70%`, `80%`, `90%`) dan bajet langkah ejen maksimum, kemudian klik **🚀 Mulakan Misi Pembelajaran Autonomi**.
3. Aliran kerja LangGraph 12-nod akan:
   - Menganalisis objektif (`goal_understanding`) dan sejarah pelajar (`profile_retrieval`).
   - Mendiagnosis jurang konsep/prasyarat (`diagnostic`) dan menjana pelan pembelajaran adaptif (`learning_plan`).
   - Memilih tindakan seterusnya secara autonomi (`orchestrator` → `teaching` / `challenge` / `prerequisite`).
   - Berhenti seketika dengan selamat pada status `WAITING_FOR_STUDENT` (melalui `interrupt()` LangGraph) apabila jawapan pelajar diperlukan, dan menyimpan titik semak atomik ke `.oyen_data/missions/{student_id}/{mission_id}.json`.
   - Menyemak jawapan pelajar secara deterministik menggunakan **SymPy** (`solver_verification`), mengemas kini skor penguasaan yang disahkan (`verified_mastery`), dan menilai semula pelan (`progress_evaluator` → `replan` / `continue` / `complete` / `terminate`).
4. Anda boleh **Jeda (Pause)**, **Sambung (Resume)**, atau **Henti (Stop)** misi pada bila-bila masa. Misi kekal tersimpan walaupun pelayar dimuat semula atau pelayan dimulakan semula.

---

## C. Pengesahan Identiti Pelajar & Firebase (Mod Awan vs Mod Tempatan)
- **Mod Tempatan / Luar Talian (`dev-local`):**
  Apabila `js/firebase-config.js` ditetapkan kepada `window.firebaseConfig = null` dan `FIREBASE_PROJECT_ID` tidak ditetapkan, pelayan berjalan dalam **Offline Dev Mode (`dev-local`)** (atau menerima pengepala pembangunan `X-Oyen-Dev-Student` untuk menguji pengasingan berbilang pelajar). Pelayan **tidak sesekali** mempercayai `student_id` daripada badan JSON permintaan untuk mengakses misi pelajar lain.
- **Mod Awan Firebase (`cloud`):**
  1. Cipta projek di [console.firebase.google.com](https://console.firebase.google.com).
  2. Aktifkan **Authentication (Email/Password)** dan **Cloud Firestore** (tampal `firestore.rules`).
  3. Masukkan konfigurasi web Firebase anda ke dalam `js/firebase-config.js` dan tetapkan `FIREBASE_PROJECT_ID=<project-id-anda>` dalam `.env`.
  4. Apabila Firebase diaktifkan, setiap permintaan ke `/api/missions/*` wajib menyertakan pengepala `Authorization: Bearer <Firebase ID Token>`. Pelayan mengesahkan token tersebut (`agents/auth.py`), mengekstrak `student_id` daripada tuntutan token yang disahkan, dan menolak akses rentas pelajar dengan kod HTTP `403 Forbidden` (serta `401 Unauthorized` bagi token yang tiada/tamat tempoh/tidak sah).
