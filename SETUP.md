# Oyen Math v3: panduan persediaan langkah demi langkah

## A. Jalankan sistem (5 minit)
1. Nyahzip `OyenMath-v3.zip`, buka terminal dalam folder `OyenMath`.
2. Pasang kebergantungan Python (sekali sahaja): `pip install -r requirements.txt`
3. Salin `.env.example` kepada `.env`, isi `ANTHROPIC_API_KEY=` (kunci dari console.anthropic.com). Tanpa kunci: ejen LangGraph berjalan dalam mod peraturan dan OCR guna Tesseract (kurang tepat).
4. `python3 server.py` kemudian buka http://localhost:8080 (port lain: `PORT=9000 python3 server.py`).
5. Ujian: `node tests/test-suite.js` dan `python3 -m unittest discover -s tests -p "test_*.py"`.
6. Semak: panel kanan "Otak Ejen" menunjukkan langkah LangGraph; jawab salah satu soalan, kotak "🧠 Ejen AI" akan muncul.

## B. Aktifkan Firebase (akaun sebenar, kemajuan awan, papan pendahulu sebenar)
Tanpa langkah ini sistem berjalan dalam MOD TEMPATAN: data dalam pelayar sahaja, kata laluan tidak disahkan, papan pendahulu ialah demo.
1. https://console.firebase.google.com → Add project.
2. Build → Authentication → Get started → Sign-in method → aktifkan **Email/Password**.
3. Build → Firestore Database → Create database (production mode).
4. Firestore → tab **Rules** → tampal kandungan `firestore.rules` → Publish.
5. Project settings (ikon gear) → Your apps → ikon `</>` (Web) → daftar app → salin objek `firebaseConfig`.
6. Buka `js/firebase-config.js`, gantikan `window.firebaseConfig = null;` dengan `window.firebaseConfig = { ...config tadi... };`
7. Authentication → Settings → Authorized domains: pastikan `localhost` ada (dan domain sebenar jika dihos).
8. Muat semula halaman, buka 🐾 profil: mesti tertulis "☁️ Mod awan". Daftar dua akaun berbeza dan semak papan pendahulu.
Nota keselamatan: peraturan Firestore menghadkan penulisan kepada baris sendiri dan lonjakan mata, tetapi mata masih dikira di pelayar. Anti-tipu penuh memerlukan pengesahan jawapan di pelayan (langkah seterusnya).

## C. Kandungan yang perlu anda semak
- Teks cerita (js/story.js) dan topik Indeks/Kuadratik: semak kesesuaian dengan guru.
- Senarai topik KSSM: semak dengan sukatan rasmi sebelum menambah topik.
