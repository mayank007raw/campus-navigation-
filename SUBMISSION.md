# SUBMISSION.md — what to submit, and how

## What the task sheet asks for

> **"Submit through GitHub wherever applicable, with a README, DECISIONS.md,
> and AI_USAGE.md."**

That is the whole requirement: **one GitHub repository, containing those
three files.** Everything else is already in place.

---

## 1. Your three required files are ready

| Required | File | What's in it |
|---|---|---|
| ✅ **README.md** | `README.md` | What the project is, how to run it, the headline result, the submission checklist |
| ✅ **DECISIONS.md** | `DECISIONS.md` | 11 numbered design decisions + a table of 7 edge cases |
| ✅ **AI_USAGE.md** | `AI_USAGE.md` | How AI was used, and a full account of where it was wrong |

Plus four files that are not required but make you look far more prepared:

| Extra | Why it helps |
|---|---|
| `HOW-IT-WORKS.md` | The project in plain English — for anyone reading without a coding background |
| `CODE-GUIDE.md` | What every file does, Dijkstra line by line |
| `EVALUATION.md` | The questions you'll be asked, with the answers |
| `SOURCES.md` | Where every fact on the map came from, with links |
| `CORRECTIONS.md` | All 12 of your corrections, in your own words |

**Nothing needs writing. Everything is done.** You are only moving files.

---

## 2. Before you submit — run this once

Open a terminal in the project folder and run:

```bash
bash run_checks.sh
```

It should print, at the very end:

```
ALL CHECKS PASSED
```

If you see that, the project works and is ready. If you see anything else,
stop and tell me before submitting.

---

## 3. Put your name on it

Right now the commit history says *"Your Name <you@example.com>"*, which is a
placeholder. One command fixes every commit at once:

```bash
bash tools/set-git-author.sh "Your Full Name" "youremail@example.com"
```

For example:

```bash
bash tools/set-git-author.sh "Aman Sharma" "aman.sharma@gmail.com"
```

Use the **same email as your GitHub account** — GitHub matches commits to
profiles by email, so your commits will then show up as yours on the
repository page. That matters: it is how the evaluator sees that *you* built
this.

> This rewrites history. Do it **before** pushing, never after.

---

## 4. Two ways to get it onto GitHub

### Route A — the git commands (recommended: keeps the full history)

The history is worth keeping. It is 23 commits, and you can see the whole
story in it — the invented first map, the gate moving, the corrections
landing one at a time. `git log --oneline` is a record of your work.

**Step 1.** Make an empty repository on GitHub:

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `campus-navigation`
3. **Do not** tick "Add a README" — leave it completely empty
4. Click **Create repository**

**Step 2.** In your project folder, run these four commands. Replace
`YOUR-USERNAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR-USERNAME/campus-navigation.git
git branch -M main
git push -u origin main
```

If it asks for a password, use a **personal access token**, not your GitHub
password — GitHub stopped accepting passwords for this in 2021:

> GitHub → your picture (top right) → **Settings** → **Developer settings**
> (bottom of the left menu) → **Personal access tokens** → **Tokens
> (classic)** → **Generate new token (classic)** → tick **repo** → Generate →
> copy it → paste it as the password.

Once it pushes, refresh the GitHub page. Your files are there.

### Route B — upload through the website (no commands at all)

Use this if the terminal is unfamiliar.

1. Go to [github.com/new](https://github.com/new), name it
   `campus-navigation`, leave it empty, click **Create repository**
2. On the next page click **uploading an existing file**
3. Unzip `campus-navigation.zip` somewhere you can find it
4. **Open the folder and select everything inside it** — all the files and
   folders — except the hidden `.git` folder, which you don't need for this
   route
5. Drag them into the browser window
6. Type a message like `Campus navigation system` and click **Commit changes**

The website upload accepts up to 100 files at a time. This project has about
60, so it will go in one go.

**The trade-off:** this route creates one single commit, so the 23-commit
history is lost. Everything else is identical — same files, same code, same
documents.

---

## 5. Make the repository public

If the evaluator has to open the link without being logged in, the repository
must be public.

**Settings** → scroll to the bottom → **Danger Zone** → **Change visibility**
→ **Change to public**.

*(If you'd rather keep it private, you must explicitly add the evaluator's
GitHub account as a collaborator under Settings → Collaborators. Public is
safer — you don't have to know their username.)*

---

## 6. Tick these off before you send the link

- [ ] `bash run_checks.sh` prints **ALL CHECKS PASSED**
- [ ] Your name is on the commits (`git log --oneline` — check the author line)
- [ ] The repository is **public**
- [ ] Opening the repo in a private/incognito browser window works
- [ ] `README.md`, `DECISIONS.md` and `AI_USAGE.md` are all visible on the
      repository front page
- [ ] The repo description (top right, "About" → gear icon) says something
      like: *"Campus Navigation System — shortest-path routing for GGSIPU
      USAR East Campus. Data traced from a screenshot + OpenStreetMap, corrected
      12 times against the real campus."*

---

## 7. What to bring to the evaluation

**Bring the screenshot.** `uploads/Screenshot_2026-10-02-12-30-38-82_*.jpg`

The map's licensing note deliberately does not redistribute Google's imagery,
so the screenshot is not in the repository. But it is the **source** of the
whole map — if the evaluator asks how you got the layout, showing them the
original picture and saying *"I traced this, and one pixel is 1.54 metres"* is
a much stronger answer than describing it.

Have it on your laptop or phone, open and ready.

**Also worth having open in tabs:**

| | |
|---|---|
| `docs/index.html` | the interactive map — click a journey and let it draw |
| `CORRECTIONS.md` | your 12 corrections, in your words |
| `SOURCES.md` | links to the screenshot, OpenStreetMap, the campus tour video, the news coverage |

---

## 8. The link to send

Once pushed, your submission is simply:

```
https://github.com/YOUR-USERNAME/campus-navigation
```

**Before you send it, open that link in a private window and check it loads.**
That is exactly what the evaluator will see.

---

## 9. If something goes wrong

| Problem | Fix |
|---|---|
| `git: command not found` | Install Git from [git-scm.com](https://git-scm.com), or use Route B |
| Push asks for a password and rejects it | Use a personal access token (§4, Route A, Step 2) |
| `remote origin already exists` | `git remote set-url origin https://github.com/YOUR-USERNAME/campus-navigation.git` |
| `failed to push some refs` | The GitHub repo was created *with* a README. Delete it and recreate it empty, or run `git pull --rebase origin main` first |
| Uploaded the wrong thing | Delete the repository (Settings → Danger Zone) and start again. It takes two minutes and costs nothing |
| Tests fail | Run it and send me the output — don't submit a red build |

---

## 10. The one-paragraph summary, if they ask you to describe the submission

> "A campus navigation system for my own college — GGSIPU USAR East Delhi
> Campus. It models the campus as a weighted graph of 12 locations and 18
> pathways, and finds the shortest walking route between any two, with
> Dijkstra as the default and BFS kept alongside it to show why the choice
> matters. The map is traced from a satellite screenshot of my campus, scaled
> using two known points so that one pixel equals 1.54 metres, with four
> buildings taken from OpenStreetMap. I corrected the map twelve times against
> the real layout, and every correction is documented in `CORRECTIONS.md`. The
> project has 80 automated tests and the three required documents."
