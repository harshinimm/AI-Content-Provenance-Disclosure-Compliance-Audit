import { Reveal } from "../components/Reveal";
import styles from "./Info.module.css";

const PIPELINE_STEPS = [
  {
    n: "01",
    title: "Scrape",
    body: "Crawl a company's site for images — same-domain, robots.txt-respecting, static HTML only.",
  },
  {
    n: "02",
    title: "Triage",
    body: "Run every image through an AI-generation classifier. Only flagged images continue — this is what makes checking hundreds of images tractable.",
  },
  {
    n: "03",
    title: "Check",
    body: "Read C2PA manifests. Run a SynthID watermark estimate. Log what's actually embedded, not what's claimed.",
  },
  {
    n: "04",
    title: "Transform",
    body: "Screenshot, recompress, crop, resize — the same casual edits any image survives on its way around the internet.",
  },
  {
    n: "05",
    title: "Re-check",
    body: "Run the same checks again. Does the disclosure signal survive, or does it quietly disappear?",
  },
  {
    n: "06",
    title: "Score",
    body: "Two independent verdicts — EU AI Act Article 50(2) and California SB 942 — plus an IP/copyright exposure flag.",
  },
];

export function Info() {
  return (
    <main>
      <section className={styles.intro}>
        <div className={`container ${styles.introInner}`}>
          <span className={`mono ${styles.eyebrow}`}>how it works</span>
          <h1 className={styles.title}>The law, and the method</h1>
          <p className={styles.sub}>
            What Article 50(2) and SB 942 actually require, and the
            six-step pipeline this tool runs against every image to test
            whether that requirement holds up in practice.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>the law</span>
            <h2 className={styles.sectionTitle}>
              Two statutes, two different bars
            </h2>
          </Reveal>
          <div className={styles.lawGrid}>
            <Reveal className={styles.lawCard}>
              <h3>EU AI Act — Article 50(2)</h3>
              <p>
                Synthetic content must be marked in a machine-readable
                format, detectable as artificially generated. The marking
                must be <em>"effective, robust, reliable, and
                interoperable, as far as technically feasible."</em>{" "}
                Persistence matters too: providers must prevent deliberate
                removal or alteration of markings. Effective August 2,
                2026 (existing systems get until Dec 2, 2026). Penalties
                up to €15M or 3% global turnover.
              </p>
            </Reveal>
            <Reveal className={styles.lawCard}>
              <h3>California SB 942</h3>
              <p>
                Applies to image, video, and audio (not text) from
                "Covered Providers" — systems with over 1M monthly CA
                users. Requires latent disclosure that's{" "}
                <em>"permanent or extraordinarily difficult to
                remove."</em> A stricter bar than the EU's effective/
                robust/reliable standard. Already in effect since January
                1, 2026. Penalties up to $5,000/day/violation.
              </p>
            </Reveal>
          </div>
        </div>
      </section>

      <section className={`${styles.section} ${styles.sectionDark}`}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>
              the method
            </span>
            <h2 className={styles.sectionTitle}>Six steps, per image</h2>
          </Reveal>
          <div className={styles.pipeline}>
            {PIPELINE_STEPS.map((step) => (
              <Reveal key={step.n} className={styles.pipelineStep}>
                <span className={`mono ${styles.pipelineN}`}>{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className="container">
          <Reveal>
            <span className={`mono ${styles.sectionLabel}`}>caveats</span>
            <h2 className={styles.sectionTitle}>What this doesn't prove</h2>
          </Reveal>
          <Reveal className={styles.caveatList}>
            <ul>
              <li>
                <strong>The SynthID check is an unofficial estimate.</strong>{" "}
                It's a third-party community classifier trained only on
                GPT-Image-2, not Google's own SynthID verifier (which has
                no public API). Accuracy on Google's own Imagen/Veo/
                Gemini-native images is unproven.
              </li>
              <li>
                <strong>The DIRE triage gate is a practical substitute — and an imperfect one.</strong>{" "}
                The paper's actual method needs a GPU/MPI pipeline and a
                checkpoint only distributed via Baidu/RecDrive (often
                unreachable, no accessible mirror). This tool uses a
                2-model classifier ensemble instead (both must agree an
                image is AI-generated), chosen after benchmarking against
                known-real and known-AI images: it cut false positives on
                real photos from 2/5 to 1/5 wrong, but recall on known-AI
                images dropped from 3/3 to 2/3. That's a real tradeoff —
                general AI-image detection genuinely struggles to
                generalize across real-world photo diversity and
                generators at once right now.
              </li>
              <li>
                <strong>Static-HTML crawl only.</strong> JS-rendered
                images and external CSS background-images aren't picked
                up — some sites' real image count is undercounted.
              </li>
              <li>
                <strong>Sample sizes are small.</strong> A handful of
                images from one crawl isn't a statistically rigorous claim
                about a company's practices — treat results as a
                methodology demonstration first.
              </li>
            </ul>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
