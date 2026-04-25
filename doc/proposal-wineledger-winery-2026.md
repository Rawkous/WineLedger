# WineLedger — Project Documentation and Winery Proposal

**Prepared for:** [Winery / stakeholder contact — relay to shareholders]  
**Date:** April 23, 2026  
**Project team:** Brian Axel Martinez (project lead), Gabriel Cruz Chavez (collaborator)  
**Repository:** https://github.com/Rawkous/WineLedger.git  

*This document is written for a shareholder and stakeholder audience. The WineLedger team presents the work as a single initiative. Phase A (current prototype) reflects implementation and architecture led by Brian Axel Martinez. Phases B and C are planned as joint delivery by the same team, with responsibilities aligned to each phase.*

---

## What WineLedger is

We are building **WineLedger** as a web application that acts as a *digital twin* of the wine supply chain. The idea is simple, and we take it seriously: every important step a bottle takes—from the vineyard through fermentation, aging, bottling, shipping, and retail—should be a **recorded event**. We link those events in an **append-only chain** of blocks, each one stamped with a cryptographic fingerprint and tied to the one before it, so that anyone with a copy of the data can see whether the story has been tampered with after the fact. We also **stream** each new event to a web browser, where a **generative** visual layer (motion, color, particles) makes the *health* of the chain of custody and the rhythm of the journey **visible**—not hidden in a spreadsheet. We place the project at the intersection of supply-chain transparency, education, and creative technology: to **explain** how wine really moves and to offer **you** a **credible, beautiful** way to show your partners and the public that the data behind the story holds together.

---

## What we have already built (Phase A — complete)

The current repository is a **working** stack, not a slide deck. **Phase A was implemented and architected** by **Brian Axel Martinez**. The **backend** is **Python** with **FastAPI**, exposing a small, clear set of **REST** endpoints: for example, you can read the full chain, run a **synthetic** supply-chain simulation, and the service verifies that the internal chain is **valid** (hashes and links are consistent). The ledger is **persistent**: blocks are written to a **JSON** file on disk, so if the server restarts, history is still there. Each block wraps a **supply-chain event** (type, time, place, metadata). The design uses **SHA-256** to link each block to the previous one, in the same spirit as better-known blockchains; in Phase A the chain is **hosted entirely in the application** for speed and clarity.

We handle **real-time updates** with **WebSockets**: when new blocks are added, connected clients receive them immediately, so the experience feels *alive* on screen. **Geography** is optional but real: events can be enriched with routing- and region-style hints through a pluggable **cache** (implemented with **SQLite**), so we can grow toward production mapping without changing the core event shape.

The **front end** is a modern static app (**Vite**) that talks to the API. **p5.js** drives the main visualization, turning each event into generative **visual parameters** (not static charts). We also provide an **educational** page about the real wine production path, aligned with the same staged journey as the simulator, so the tool works for teaching as well as demos.

**In one sentence, Phase A is what we have today:** a local-to-server prototype with a real API, a persisted hash-linked ledger, live streaming to the browser, and generative art driven by the same data the ledger stores.

---

## Why we are anchoring the public record on an Ethereum Layer 2

In our roadmap, the next move is an **EVM**-compatible **Layer 2 (L2)** network: a rollup that sits on top of Ethereum, inherits its security model in broad terms, and gives us **much lower and steadier** costs for the operations we need—storing a **Merkle root**, a **commitment to a batch of events**, or a **pointer** to a file that holds the full story.

**We are standardizing on Base** as the L2 for on-chain work. It is an EVM chain we can use with the same tools we already use (including **Solidity**), with fees that stay **practical** for scheduled anchoring and for optional **NFT** mints, without asking a winery to pay mainnet prices for day-to-day integrity.

**We want to be clear:** we do *not* need to post every field-level sensor row on the chain. We will keep the **authoritative, detailed** history in the WineLedger service and in durable storage; we will use the **L2** for **verifiable commitments** (and, if you want them, **ownership** of digital collectibles) so that a neutral observer can check that a given export or public story matches a **time-stamped** on-chain record.

---

## How we use Solidity on Base (our own smart contracts)

We write contracts in **Solidity** for EVM networks such as Base. We will ship **our own** small, auditable set of contracts instead of depending on generic third-party dApps for the core story. The design stays easy to explain: **on-chain, we store the “seals” and the “tickets”; off-chain, we store the full book.**

We will deploy a **provenance / anchor contract** in Solidity to record **commitments** from the running service—for example, the root hash of a **Merkle tree** over a batch of events, or a hash of a **snapshot** file in the cloud. Each commit is **one** L2 transaction per batch (or per milestone we agree on with you), not one transaction per line item. The contract will emit **events** (log lines that indexers and explorers read) so that you, your partners, or the public can see **when** a new batch was sealed and **link** that seal to the off-line data we publish for you.

For **optional** campaigns—limited art tied to a vintage or a route—we can deploy a separate **ERC-721**-style **NFT** contract in Solidity to mint **collectibles** on Base, with **metadata** that points to A.I.-generated or generative art and, where appropriate, back to the same **commitment** or bottle identifier. We can encode **royalties and allowlists** in the contract layer so you keep control of how tokens are used in marketplaces. None of this replaces the need for a sound legal and brand policy, but we can give you a **clean technical** story: the chain holds **hashes, pointers, and ownership**; you hold **narrative and law**.

---

## Phase B — The plan: production on AWS and live anchoring to Base

**Our goal in Phase B** is to run WineLedger as a **private, professionally operated** system in the cloud, and connect it to **Base** with **our** custom Solidity contracts so that integrity is not only “inside our server” but can be **checked from outside** using public tools and standard wallets. **Brian Axel Martinez and Gabriel Cruz Chavez** will lead execution of **Phases B and C** as a coordinated team.

**What we will deliver in Phase B**

- **Hosting:** We will run the FastAPI app on **Amazon Web Services** inside a **VPC** (isolated network). We will put the API behind a **load balancer** with **TLS**; we will support **WebSockets** end-to-end for live demos. We will set up autoscaling and health checks so the service stays stable when traffic spikes (for example, an event or harvest season).
- **Data path:** We will keep the existing JSON ledger (or a managed database) as the **operational** source of truth; we will use **S3** (or equivalent object storage) for **exports**, **snapshots**, and large **geo** artifacts. We will put **secrets** (API keys, deploy keys) in a **secret manager**, not in source code.
- **On-chain path:** We will run a **relayer** process (a small, audited service) that **only** our deployment can use to post **Merkle roots** or file hashes to our **provenance** Solidity contract on **Base** on a **fixed schedule** or at **business milestones** (for example, “lot bottled,” “pallet shipped”).
- **Security:** We will use **least-privilege** access for people and for machines, **MFA** for operations, a **WAF** in front of public endpoints, **encryption at rest and in transit**, **centralized logging** and **audit** trails, and we will publish a **responsible disclosure** path before go-live so security researchers and partners can report issues in a **coordinated** way.
- **Outcome we are aiming for:** you can **use** the product every day, **back it up and restore** it, and **point** to a **Base** address where independent parties verify that the batches we publish for you match on-chain commitments.

---

## Phase C — Durable media, A.I. imagery, NFTs, and live generative video

**Our goal in Phase C** is to turn the data and commits from Phase B into a **full creative and collectible layer** while keeping the rule the same: the **detailed** ledger and files stay off-chain, and **Base** holds **verifiability and optional ownership**. This phase is **joint delivery** by **Brian Axel Martinez and Gabriel Cruz Chavez**, building on the operational foundation from Phase B.

**What we will deliver in Phase C**

- **Durable and shareable data tier:** We will set up long-lived storage for **versioned** geo data, **ledger snapshots**, and A.I. outputs; we are already planning the same abstractions in the codebase for a national or institutional **data** tier, and in Phase C we will implement that concretely on **S3**-class storage with lifecycle and access policies you control.
- **A.I.-assisted still imagery:** We will run a **dedicated** inference pipeline (isolated from the core API) to generate label art, campaign stills, or “vintage” images **driven by** or **consistent with** your real milestone data. We will store each asset with a **content hash**; we will make **metadata** reference the **batch or product** and, when it applies, the **Merkle root** or anchor already on **Base**. We will work with you on **legal and brand** rules for licensing, A.I. disclosure where required, and your ownership of the **brand** itself.
- **NFT program (on Base, via our Solidity):** if you want a **collectible** program, we will use the same L2 for **minting** so fees stay low, with **clear** links between **token**, **art**, and the **provenance** commitment. We will keep the **on-chain** part small; we will point the **art file** with a **URI** (for example **IPFS** or private storage, depending on your policy).
- **Live generative video:** We will use the **same** event stream that already feeds **p5.js** in the browser and scale it to **venue** use: long-form generative **motion** for tasting rooms and retail **screens**, with **WebSockets** for in-browser real-time, and, where you need it, **GPU-backed** headless **encoding** to **HLS** or **WebRTC** for multiple displays. The **WineLedger** API will stay the **single** source of truth, and we will keep heavy work **isolated** so live traffic never chokes the ledger.

---

## How we see the project as a whole

We are telling **one** story in three layers. The **first layer** is the **data and the chain of blocks** the application runs today: events, hashes, persistence, and validation. The **second layer** is **trust at scale**: the same story **anchored** to **Base** with **our** Solidity contracts, deployed from **AWS**, with the security and operations we described above. The **third layer** is **culture and memory**: A.I. art, **NFTs** that mean something because they point to that history, and **generative video** that makes the supply chain *felt* in a room full of people. We are not asking you to bet on a single magic word like “blockchain”; we want you to see **what we have built**, **what we will do next**, and **how** each piece earns its place in the **plain language** of wine, proof, and experience.

---

*Prepared for distribution to shareholders and partners; we will add letterhead, final security contact for responsible disclosure, and any NDA or legal addenda at go-live.*
