# 🗺️ Skill Manager: Categorization & Emoji Guide

This document defines the categorization logic, visual identity, and emoji mapping system for the Skill Manager. It serves as the single source of truth for UI implementation and automatic skill classification.

---

## 🎨 Visual Identity Standard

The Skill Manager utilizes a standard emoji-based visual identification system. This ensures a consistent, lightweight, and universally compatible design across all platforms and themes.

### Emoji Resolution
Every category is mapped to a specific emoji. These emojis are used in:
- **Library View**: Section headers and skill list items.
- **Quick Copy View**: Sidebar category icons.
- **Search Results**: Immediate visual context for found skills.

Logic is managed via `AppController.getCategoryEmoji(name)` in `src/skill_manager/app.py`.

---

## 🤖 Two-Stage Categorization System

The Skill Manager automatically classifies skills into a strict two-stage hierarchy (`Main Category` -> `Sub Category`) based on their content if no explicit category is provided in the frontmatter.

### Main Categories
The system uses 6 primary Main Categories to group related sub-categories:
1. 🛠️ **Core Engineering & Technology**
2. 📈 **Business & Operations**
3. 🛡️ **Quality & Data**
4. 📚 **Content & Knowledge**
5. 🧘 **Specialized & Lifestyle**
6. ⚙️ **System & Workflow**

### Matching Logic
The system uses a weighted keyword frequency algorithm defined in `src/skill_manager/core/parsing.py`:
1. **Input Normalization**: Markdown bold/italic markers (`**`, `_`) are stripped before matching.
2. **Weighted Analysis**: The skill `name` is weighted 2x more than the `description`.
3. **Keyword Scanning**: The combined text is scanned against the global hierarchical keyword dictionary.
4. **Two-Stage Resolution**:
   - The algorithm maps keywords to a specific Sub Category.
   - The Sub Category automatically resolves its parent Main Category.
5. **Emoji Resolution**:
   - **Exact Match**: Direct mapping for standardized names.
   - **Case-Insensitive Match**: Resilience against naming variations.
   - **Substring Match**: Supports aliases (e.g., "Web Dev" matches "Web Development").

### Global Category & Keyword Reference

#### 🛠️ Core Engineering & Technology (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **AI** | 🧠 | `ai`, `ia`, `llm`, `rag`, `prompt`, `model`, `claude`, `openai`, `gemini`, `anthropic`, `hugging face`, `vision model`, `computer vision`, `yolo`, `sam`, `notebooklm` |
| **Agents** | 🤖 | `agent`, `agents`, `subagent`, `subagents`, `mcp`, `crewai`, `langchain`, `context window`, `agentes` |
| **Architecture** | 🏛️ | `architect`, `senior architect`, `project architect`, `architecture`, `architecture diagram`, `architecture patterns`, `system design`, `c4`, `adr`, `decision record`, `domain-driven`, `ddd`, `cqrs`, `event sourcing`, `bounded context`, `monorepo` |
| **Backend Development** | ⚙️ | `backend`, `rails`, `node`, `api`, `fastapi`, `full-stack` |
| **Cloud Infrastructure** | ☁️ | `docker`, `kubernetes`, `k8s`, `aws`, `azure`, `gcp`, `cloud`, `cloudflare`, `terraform`, `linux`, `server`, `istio`, `service mesh` |
| **DevOps** | ♾️ | `devops`, `ci/cd`, `ci`, `cd`, `deploy`, `deployment`, `on-call`, `runbook`, `incident`, `slack`, `tmux` |
| **Developer Tools** | 🧰 | `git`, `github`, `pr`, `pull request`, `commit`, `issue`, `dx`, `developer experience`, `file organizer`, `vexor`, `semantic file discovery`, `cli`, `tool`, `tools`, `comprehensive review` |
| **Programming Languages** | ⌨️ | `python`, `typescript`, `javascript`, `rust`, `go`, `golang`, `c-pro`, `c code`, `c++`, `c#`, `java`, `ruby`, `php`, `elixir`, `haskell`, `julia`, `memory safety`, `memory-safe` |
| **Web Development** | 🌐 | `web`, `frontend`, `react`, `next.js`, `tailwind`, `css`, `ui`, `ux`, `fullstack`, `angular`, `vue`, `html`, `website`, `portfolio`, `wordpress`, `three.js`, `threejs`, `webgl` |
| **Mobile Development** | 📱 | `mobile`, `ios`, `android`, `flutter`, `expo`, `react native`, `swift`, `swiftui`, `swiftpm`, `app store`, `aso`, `kotlin` |
| **Desktop Development** | 🖥️ | `desktop`, `electron`, `avalonia`, `makepad`, `robius` |
| **Embedded Systems** | 📟 | `embedded`, `firmware`, `arm cortex`, `microcontroller` |
| **Web3** | ⛓️ | `blockchain`, `web3`, `defi`, `nft`, `smart contract`, `bitcoin`, `lightning`, `wallet` |
| **Game Development** | 🎮 | `game`, `unity`, `godot`, `unreal` |
| **Shell Scripting** | 🐚 | `posix`, `bash`, `powershell`, `busybox`, `windows`, `shell`, `jq` |
| **Build Systems** | 🏗️ | `bazel`, `nx`, `turborepo` |
| **Background Jobs** | ⏱️ | `inngest`, `background jobs`, `queues`, `durable execution` |

#### 📈 Business & Operations (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Business Strategy** | ♟️ | `business`, `sales`, `cro`, `monetization`, `pricing`, `price`, `churn`, `retention`, `growth` |
| **Marketing** | 📢 | `marketing`, `seo`, `ads`, `ad creative`, `paid ads`, `google ads`, `meta`, `linkedin`, `tiktok`, `influencer`, `lead generation`, `leads`, `cold email`, `copywriting`, `headline`, `subject line`, `campaign`, `audience`, `brand reputation`, `aso`, `awareness` |
| **Product Management** | 📈 | `product`, `startup`, `saas`, `micro-saas`, `jtbd`, `jobs-to-be-done`, `customer`, `market`, `competitive`, `brand`, `persona`, `idea`, `darwin`, `personal tool` |
| **Finance** | 💰 | `finance`, `financial`, `trading`, `investment`, `buffett` |
| **Legal** | ⚖️ | `legal`, `law`, `contract`, `compliant`, `jurid`, `direito`, `advogado`, `criminal`, `trabalhista`, `tributario`, `consumidor`, `imobiliario`, `civil`, `leilao`, `leilões`, `edital`, `nulidades`, `cpc`, `lei` |
| **Compliance** | 📜 | `compliance`, `audit`, `access review`, `pci`, `policy` |
| **Logistics** | 📦 | `logistics`, `freight`, `carrier`, `returns`, `reverse logistics` |
| **Procurement** | 🛒 | `procurement`, `purchase`, `energy procurement` |
| **Billing** | 💳 | `billing`, `invoice` |
| **Payments** | 💸 | `payment`, `paypal`, `stripe`, `tax` |
| **ERP** | 🏢 | `odoo`, `erp`, `timesheet` |
| **Human Resources** | 👥 | `employment`, `hr`, `payroll` |
| **Inventory** | 🏬 | `inventory`, `demand planning`, `warehouse` |
| **Manufacturing** | 🏭 | `production scheduling`, `manufacturing` |
| **Careers** | 💼 | `interview`, `job search`, `resume`, `career` |

#### 🛡️ Quality & Data (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Security** | 🛡️ | `security`, `hack`, `vulnerability`, `pentest`, `penetration`, `auth`, `xss`, `threat`, `risk`, `attack`, `red team`, `active directory`, `kerberos`, `forensics`, `incident response`, `privilege escalation`, `secrets`, `credentials`, `mtls`, `zero-trust`, `shodan` |
| **Testing** | 🧪 | `test`, `testing`, `qa`, `e2e`, `playwright`, `cypress`, `jest`, `tdd`, `validation`, `acceptance`, `verify` |
| **Debugging** | 🐞 | `debug`, `debugging`, `error`, `stack traces`, `bug`, `error detective`, `logs`, `root cause` |
| **Performance** | 🏎️ | `performance`, `performance bottlenecks`, `performance optimizer`, `profiling` |
| **Observability** | 🔭 | `observability`, `monitor`, `monitoring`, `prometheus`, `slo`, `tracing`, `jaeger`, `tempo` |
| **Code Quality** | 🧹 | `technical debt`, `legacy`, `modernizer`, `refactor`, `clean code`, `code quality` |
| **Linting** | ✨ | `shellcheck`, `linting`, `lint` |
| **Quality Control** | 💎 | `quality control`, `non-conformance` |
| **Migration** | 🛫 | `migration`, `code migration`, `framework migration` |
| **Analytics** | 📊 | `analytics`, `backtesting`, `spreadsheet`, `xlsx` |
| **Data** | 🧊 | `data`, `vector`, `warehouse`, `forecast`, `analysis`, `analyze` |
| **Databases** | 🗄️ | `sql`, `postgres`, `mysql`, `database`, `dbt` |

#### 📚 Content & Knowledge (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Content** | 📝 | `content`, `writing`, `blog`, `article`, `video`, `audio`, `gif`, `favicon`, `unsplash`, `remotion`, `portfolio`, `rsvp`, `speed reader` |
| **Documentation** | 📚 | `documentation`, `docs`, `readme`, `wiki`, `onboarding`, `obsidian`, `markdown`, `latex`, `paper`, `docx`, `pptx`, `office`, `document` |
| **Knowledge Management** | 💡 | `summarizer`, `explain`, `socratic`, `bullet`, `knowledge`, `context`, `context save`, `context restore`, `diary`, `logger` |
| **Diagrams** | 🗺️ | `mermaid`, `diagram` |
| **Design** | 🎨 | `design`, `canvas`, `canva`, `art`, `figma`, `theme`, `visual`, `hig`, `human interface guidelines` |
| **Communications** | 📧 | `communication`, `communication mode`, `internal comms`, `communications`, `brief`, `terse`, `caveman`, `status reports` |
| **Social Media** | 💬 | `social`, `twitter`, `youtube`, `publisher`, `x/twitter` |
| **Localization** | 🌍 | `i18n`, `localization`, `translation`, `locale`, `rtl` |

#### 🧘 Specialized & Lifestyle (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Psychology** | 🧩 | `psychology`, `psychologist`, `identity`, `trust`, `calibrator`, `assumption`, `auditor`, `first-principles`, `emotional arc`, `loss aversion`, `objection`, `pitch`, `scarcity`, `urgency`, `sequence` |
| **Health** | 🩺 | `health`, `medical`, `clinical`, `hospital`, `emergency`, `medical card`, `goal analyzer`, `健康`, `医疗`, `急救` |
| **Mental Health** | 🧘 | `mental health`, `心理` |
| **Fitness** | 🏋️ | `fitness`, `nutrition`, `weightloss`, `营养` |
| **Sleep** | 🌙 | `sleep`, `睡眠` |
| **Rehabilitation** | 🩹 | `rehabilitation`, `康复` |
| **Traditional Medicine** | 🌿 | `tcm`, `体质` |
| **Occupational Health** | 👷 | `occupational health` |
| **Oral Health** | 🦷 | `oral health`, `口腔` |
| **Sexual Health** | 🏥 | `sexual health` |
| **Travel Health** | ✈️ | `travel health` |

#### ⚙️ System & Workflow (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Core Workflow** | 🔄 | `plan`, `planning`, `brainstorm`, `brainstorming`, `constructive work`, `kaizen`, `essential`, `questions`, `underspecified`, `verification`, `completion`, `task`, `workflow`, `conductor`, `build`, `project guidelines`, `sharp edges`, `speckit`, `updater` |
| **Uncategorized** | 📁 | (Default fallback) |

---

## 🖥️ UI Implementation Details

### 1. Special Sections (Hardcoded Identifiers)
The `SkillModel` and QML layer recognize several "system" sections that bypass standard category logic:

| Section | Header Emoji | Item Icon | Description |
| :--- | :---: | :---: | :--- |
| **Essentials** | ⭐ | ★ | High-priority skills (pinned to top). Golden tinted header. |
| **Collections** | 📦 | 📦 | Bundled skill sets (bundles). |
| **Custom Commands** | ⚡ | ⚡ | Specialized executable skills. |

### 2. Supported Aliases
The `getCategoryEmoji` logic supports common shorthand aliases for developer productivity:

- `Backend Dev` -> `Backend Development` (`⚙️`)
- `Web Dev` -> `Web Development` (`🌐`)
- `Cloud Infra` -> `Cloud Infrastructure` (`☁️`)
- `Product Mgmt` -> `Product Management` (`📈`)
- `Game Dev` -> `Game Development` (`🎮`)
- `Desktop Dev` -> `Desktop Development` (`🖥️`)
- `Knowledge Mgmt` -> `Knowledge Management` (`💡`)
- `Mobile Dev` -> `Mobile Development` (`📱`)
- `Programming` -> `Programming Languages` (`⌨️`)

### 3. Collapsing & Sorting Logic (Two-Stage)
- **State Persistence**: Collapsed states for both Main Categories and Sub Categories are stored in the user configuration.
- **Section Sorting**: 
  - Main Categories are sorted according to a predefined priority (System > Engineering > Business > Data > Knowledge > Lifestyle).
  - Sub Categories are sorted alphabetically within their Main Category.
  - **Essentials**, **Collections**, and **Custom Commands** are forced to the top as pseudo-Main Categories.

---

## 🛠️ Developer Guide

### How to Manually Categorize a Skill
Add the `category` field to the markdown frontmatter.

```markdown
---
name: My Awesome Skill
description: Does something cool.
category: Architecture
---
# Skill Content...
```

### How to Add a New Category
1. **Define Logic**: Add the category and keywords to `CATEGORIES` in `src/skill_manager/core/parsing.py`.
2. **Assign Visuals**: Update the `mapping` in `AppController.getCategoryEmoji` in `src/skill_manager/app.py`.
3. **Verify Sync**: Run the `verify_sync.py` script in the `scratch/` directory to ensure parity between code and documentation.
