# Naveen Gadde: personal website

A simple, fast website for your writing: the weekly *A Thought Experiment*
series, your frameworks and an About page. It's free to host on GitHub Pages,
and after setup everything happens in your web browser. **No Terminal needed.**

When you add or edit a file on GitHub, the site rebuilds and republishes itself
in about a minute.

---

## What's in this folder

| Item | What it is |
|---|---|
| `site.json` | Your name, tagline, LinkedIn link and web address. **Edit this first.** |
| `posts/` | One file per post. `_TEMPLATE.md` shows the format. |
| `frameworks/` | One file per framework (The Question Loop is already there). |
| `pages/about.md` | Your About page. |
| `templates/`, `static/` | Page layouts, styling and fonts. You won't need to touch these. |
| `build.py` | Turns your text files into the website. GitHub runs it for you. |
| `scripts/import_linkedin.py` | Converts your LinkedIn data export into post files. |
| `.github/workflows/deploy.yml` | Tells GitHub to rebuild and publish the site automatically. |

---

## 1. Put the site online (one time, about 20 minutes)

**Step 1. Create a GitHub account**
Go to https://github.com and sign up (free). Your username becomes part of
your web address: `https://USERNAME.github.io`. Pick something professional,
such as `naveengadde`.

**Step 2. Create the repository (the site's folder on GitHub)**
1. Click the **+** at the top right > **New repository**.
2. Repository name: exactly `USERNAME.github.io`, using your own username.
3. Choose **Public**. Leave everything else unchanged and click **Create repository**.

**Step 3. Upload the files**
1. On the new repository page, click **uploading an existing file**.
2. Open this unzipped folder in Finder, select everything inside it
   (`Cmd + A`) and drag it into the browser window.
3. Scroll down and click **Commit changes**.

**Step 4. Add the auto-publish file**
Finder hides folders whose names start with a dot, so the `.github` folder
probably wasn't uploaded. Add it by hand:
1. In your repository, click **Add file** > **Create new file**.
2. In the name box, type exactly: `.github/workflows/deploy.yml`
   (typing the `/` creates the folders).
3. Open `.github/workflows/deploy.yml` from this folder in TextEdit. In
   Finder, press `Cmd + Shift + .` to show hidden folders. Copy all of its
   text and paste it into the GitHub editor.
4. Click **Commit changes**.

**Step 5. Turn on GitHub Pages**
1. In the repository, go to **Settings** > **Pages** (left menu).
2. Under **Build and deployment** > **Source**, choose **GitHub Actions**.

**Step 6. Fill in your details**
1. In the repository, click `site.json` and then the pencil icon to edit.
2. Replace `YOUR-GITHUB-USERNAME` in `url` with your username.
3. Replace `YOUR-LINKEDIN-ID` in `linkedin_url` with your LinkedIn profile
   address (copy it from your LinkedIn profile page).
4. Adjust `tagline` if you want different words on the homepage.
5. Click **Commit changes**.

**Step 7. Check it's live**
Open the **Actions** tab. A run called "Publish site" appears; when it shows a
green check (about a minute), visit `https://USERNAME.github.io`.

If it shows a red ✗, click it to see the message. It usually names the file
and line that needs fixing.

---

## 2. Add your LinkedIn posts

**All past posts at once (recommended):**
1. LinkedIn > **Me** > **Settings & Privacy** > **Data privacy** >
   **Get a copy of your data**. Request the archive. LinkedIn emails you
   when it's ready, which can take up to a day.
2. Download it, unzip it and find **Shares.csv**.
3. Send Shares.csv to Claude and ask it to convert the posts. You'll get back
   post files to upload into the `posts/` folder on GitHub (**Add file** >
   **Upload files**).

The converter recognises the *A Thought Experiment* series and turns the
second line into the title. It keeps your line breaks, turns hashtags into
tags, links back to the original LinkedIn post, and skips reposts and
connections-only posts. Re-running it later only adds new posts.

**One new post each week:**
1. In the repository, open the `posts` folder > **Add file** > **Create new file**.
2. Name it with the date first: `2026-11-10-winning-over-winners.md`.
3. Paste this at the top, then your post text below it:
   ```
   ---
   title: Winning Over Winners
   series: thought-experiment
   linkedin_url: (paste the link to the LinkedIn post)
   ---
   ```
4. **Commit changes**. The site updates in about a minute.

**Scheduling posts in advance:** give the file a future date, e.g.
`2026-11-17-right-questions-vs-right-answers.md`. It stays hidden and appears
automatically on that date: the site rebuilds itself every morning around
6–7am Central. Add the `linkedin_url` line later, once the LinkedIn post is
live, and the "Join the discussion on LinkedIn" button appears.

Note: the repository is public, so anyone who digs through its files on
GitHub could read a scheduled post before its date. The website itself won't
show it. GitHub also pauses the daily rebuild if a repository has no changes
for 60 days; adding a post restarts it.

**Adding the post's image:** upload the image into `static/posts/` (in
GitHub: open that folder > **Add file** > **Upload files**), then add two lines
to the post's `---` block:
```
image: posts/your-image-name.jpg
image_alt: A one-sentence description of the image for screen readers
```
The image shows above the post and becomes the preview picture when the link
is shared on LinkedIn. JPG or PNG, ideally under 500 KB.

To fix a typo, open the post file on GitHub, click the pencil, edit, and commit.
To hide a post without deleting it, add `draft: true` inside the `---` block.

---

## 3. Use your own domain (optional, about $10–20 a year)

1. Buy a domain from any registrar (e.g. Cloudflare, Namecheap, Squarespace Domains).
2. At the registrar, add these DNS records:
   - Four **A** records for `@` pointing to `185.199.108.153`,
     `185.199.109.153`, `185.199.110.153` and `185.199.111.153`
   - One **CNAME** record for `www` pointing to `USERNAME.github.io`
3. In `site.json`, set `"custom_domain": "yourdomain.com"` and commit.
4. GitHub > **Settings** > **Pages** > **Custom domain**: enter it and save.
   After the check passes (minutes to a few hours), tick **Enforce HTTPS**.

GitHub's help page "Managing a custom domain for your GitHub Pages site" has
screenshots if you get stuck.

---

## 4. Connect it to LinkedIn

- Profile > **Contact info** > **Website**: add the address.
- Profile > **Featured** > **Add a link**: your homepage and The Question Loop page.
- Headline or About section: mention "Essays and frameworks at yourdomain.com".
- When you post, put the site link in the first comment rather than the post
  itself. LinkedIn tends to show posts with outside links to fewer people.
- Link previews use each page's title and summary. Add `summary:` to a post's
  `---` block to control what LinkedIn shows.

---

## 5. Before you share it

- [ ] Read the About page (`pages/about.md`). It highlights your U.S. experience.
      Make sure every detail is accurate and something you're comfortable
      making public, especially employer names and the $700K figure.
- [ ] Read the homepage introduction (`templates/home.html`, the paragraph
      starting "I write a weekly series") and the tagline in `site.json`.
- [ ] Upload your posts.

---

## Previewing on your computer (optional)

```
pip3 install -r requirements.txt
python3 build.py --serve
```

Open http://127.0.0.1:8000. To run the automated checks: `python3 -m pytest -q`.
