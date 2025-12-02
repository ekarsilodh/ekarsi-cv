# Ekarsi Lodh – Academic CV Website

This repository hosts my academic CV website, built using a single `index.html`
file and served via **GitHub Pages**.  
All content (CV sections, publications, projects, buttons, logos) is manually
editable inside the HTML file.

---

## 📁 Repository Structure

```
/assets
   ├─ EkarsiLodhCV2025.pdf      # Downloadable CV
   ├─ Github_CV .png            # Website icon (optional)
index.html                      # Main website (all sections)
README.md                       # This file
```

---

## ✏️ How to Edit the Website

Everything is inside **index.html**.  
Each major CV section is wrapped in a `<section id="...">` block so it’s easy to find.

### Sections (Search inside index.html)

| Section | Search this ID | Location |
|--------|----------------|----------|
| Hero / Header | `hero` | Top summary, address, buttons |
| Education | `id="education"` | Edit degrees |
| Research Experience | `id="research"` | Edit internship + project |
| Projects | `id="projects"` | Streamlit app, pipelines |
| Journal Publications | `id="pubs-journal"` | Full ordered list |
| Conference Papers | `id="pubs-conference"` | Full ordered list |
| Memberships | `id="memberships"` | IEEE etc. |
| Leadership | `id="leadership"` | CR, Convenor, Ambassador |
| Skills | `id="skills"` | Each skill has its own card |
| Competitions | `id="competitions"` | Achievements & hackathons |
| Certifications | `id="certifications"` | Coursera, etc. |
| Extracurriculum | `id="extracurriculum"` | Activities |
| Contact | `id="contact"` | Email footer |

To edit content, simply replace the text inside `<div class="card-body">...</div>`.

---

## 🔗 Updating the Social Buttons

Search for:

```
<div class="hero-links">
```

Inside it you can update URLs for:

- LinkedIn  
- GitHub  
- ORCID  
- Google Scholar  
- CV download button  

Each button uses an inline SVG icon (you can replace the SVG if needed).

---

## 📘 Updating Publications

Journal and conference publications are simple `<ol><li>...</li></ol>` lists.

To add a new one:

1. Go to the correct section:  
   `id="pubs-journal"` or `id="pubs-conference"`
2. Copy-paste an existing `<li>` block
3. Update authors, title, journal, and DOI  
4. Wrap the DOI in a clickable link:

```html
<a href="https://doi.org/XXXXX" target="_blank">10.xxxx/yyyy</a>
```

---

## 🚀 Updating the Projects Section

Search for:

```
id="projects"
```

Each project is one `.card` block.

To add a new project:

1. Duplicate an existing card  
2. Update:
   - `card-title`
   - `card-subtitle`
   - bullet points
   - GitHub link
   - (optional) Streamlit Launch button

---

## 🌐 Updating the Favicon

Place your favicon inside **/assets** as:

```
favicon.png   (or favicon.svg)
```

Then make sure these lines exist inside `<head>`:

```html
<link rel="icon" type="image/png" href="assets/favicon.png">
<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
```

GitHub Pages sometimes caches favicons — use **Ctrl+Shift+R** to refresh.

---

## 🛠️ Deploying / Redeploying with GitHub Pages

GitHub Pages automatically rebuilds on every commit.

If you ever need to enable/verify:

1. Go to **Settings → Pages**
2. Source:  
   ```
   Deploy from branch
   Branch: main
   Folder: /root
   ```
3. Save

Your site will be available at:

```
https://<your-username>.github.io/<repository-name>/
```

---

## 🧰 Editing Tips

- Use **VS Code** with HTML formatting for easiest editing  
- Always commit changes in small steps (helps rollback)  
- Keep the `/assets` folder clean  
- For new icons, prefer **SVG** (better quality + smaller file)  

---

## 💬 Contact

If you’re viewing this repo and have questions, feel free to reach out:

📧 exl533@student.bham.ac.uk  
🔗 https://www.linkedin.com/in/ekarsi24
