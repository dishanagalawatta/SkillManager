# Skill Manager: Categorization & Emoji Guide

This document defines the categorization logic, visual identity, and emoji mapping system for the Skill Manager. It serves as the single source of truth for UI implementation and automatic skill classification.

---

## Visual Identity Standard

The Skill Manager utilizes a standard emoji-based visual identification system. This ensures a consistent, lightweight, and universally compatible design across all platforms.

### Emoji Resolution
Every category is mapped to a specific emoji. These emojis are used in:
- **Library View**: Section headers and skill list items.
- **Quick Copy View**: Sidebar category icons.
- **Search Results**: Immediate visual context for found skills.

Logic is managed via `get_category_emoji()` in `src/skill_manager/core/categories.py`.

---

## Two-Stage Categorization System

The Skill Manager automatically classifies skills into a strict two-stage hierarchy (`Main Category` -> `Sub Category`) based on their content if no explicit category is provided in the frontmatter.

### Main Categories
The system uses 6 primary Main Categories to group related sub-categories:
1. **Core Engineering & Technology**
2. **Business & Operations**
3. **Quality & Data**
4. **Content & Knowledge**
5. **Specialized & Lifestyle**
6. **System & Workflow**

### Matching Logic
The system uses a weighted keyword frequency algorithm defined in `src/skill_manager/core/parsing/categorizer.py`:
1. **Input Normalization**: Markdown bold/italic markers (`**`, `_`) are stripped before matching.
2. **Weighted Analysis**: The skill `name` is weighted 2x more than the `description`.
3. **Keyword Scanning**: The combined text is scanned against the global hierarchical keyword dictionary.
4. **Two-Stage Resolution**:
   - The algorithm maps keywords to a specific Sub Category.
   - The Sub Category automatically resolves its parent Main Category.
5. **Emoji Resolution**:
   - Exact Match: Direct mapping for standardized names.
   - Case-Insensitive Match: Resilience against naming variations.
   - Substring Match: Supports aliases (e.g., "Web Dev" matches "Web Development").

### Global Category & Keyword Reference

#### Core Engineering & Technology (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **AI** | :brain: | `ai`, `ia`, `llm`, `rag`, `prompt`, `model`, `claude`, `openai`, `gemini`, `anthropic`, `hugging face`, `vision model`, `computer vision`, `yolo`, `sam`, `notebooklm` |
| **Agents** | :robot: | `agent`, `agents`, `subagent`, `subagents`, `mcp`, `crewai`, `langchain`, `context window`, `agentes` |
| **Architecture** | :classical_building: | `architect`, `senior architect`, `project architect`, `architecture`, `architecture diagram`, `architecture patterns`, `system design`, `c4`, `adr`, `decision record`, `domain-driven`, `ddd`, `cqrs`, `event sourcing`, `bounded context`, `monorepo` |
| **Backend Development** | :gear: | `backend`, `rails`, `node`, `api`, `fastapi`, `full-stack` |
| **Cloud Infrastructure** | :cloud: | `docker`, `kubernetes`, `k8s`, `aws`, `azure`, `gcp`, `cloud`, `cloudflare`, `terraform`, `linux`, `server`, `istio`, `service mesh` |
| **DevOps** | :infinity: | `devops`, `ci/cd`, `ci`, `cd`, `deploy`, `deployment`, `on-call`, `runbook`, `incident`, `slack`, `tmux` |
| **Developer Tools** | :toolbox: | `git`, `github`, `pr`, `pull request`, `commit`, `issue`, `dx`, `developer experience`, `file organizer`, `vexor`, `semantic file discovery`, `cli`, `tool`, `tools`, `comprehensive review` |
| **Programming Languages** | :keyboard: | `python`, `typescript`, `javascript`, `rust`, `go`, `golang`, `c-pro`, `c code`, `c++`, `c#`, `java`, `ruby`, `php`, `elixir`, `haskell`, `julia`, `memory safety`, `memory-safe` |
| **Web Development** | :globe_with_meridians: | `web`, `frontend`, `react`, `next.js`, `tailwind`, `css`, `ui`, `ux`, `fullstack`, `angular`, `vue`, `html`, `website`, `portfolio`, `wordpress`, `three.js`, `threejs`, `webgl` |
| **Mobile Development** | :mobile_phone: | `mobile`, `ios`, `android`, `flutter`, `expo`, `react native`, `swift`, `swiftui`, `swiftpm`, `app store`, `aso`, `kotlin` |
| **Desktop Development** | :desktop_computer: | `desktop`, `electron`, `avalonia`, `makepad`, `robius` |
| **Embedded Systems** | :pager: | `embedded`, `firmware`, `arm cortex`, `microcontroller` |
| **Web3** | :chains: | `blockchain`, `web3`, `defi`, `nft`, `smart contract`, `bitcoin`, `lightning`, `wallet` |
| **Game Development** | :video_game: | `game`, `unity`, `godot`, `unreal` |
| **Shell Scripting** | :shell: | `posix`, `bash`, `powershell`, `busybox`, `windows`, `shell`, `jq` |
| **Build Systems** | :building_construction: | `bazel`, `nx`, `turborepo` |
| **Background Jobs** | :stopwatch: | `inngest`, `background jobs`, `queues`, `durable execution` |

#### Business & Operations (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Business Strategy** | :chess_pawn: | `business`, `sales`, `cro`, `monetization`, `pricing`, `price`, `churn`, `retention`, `growth` |
| **Marketing** | :loudspeaker: | `marketing`, `seo`, `ads`, `ad creative`, `paid ads`, `google ads`, `meta`, `linkedin`, `tiktok`, `influencer`, `lead generation`, `leads`, `cold email`, `copywriting`, `headline`, `subject line`, `campaign`, `audience`, `brand reputation`, `aso`, `awareness` |
| **Product Management** | :chart_with_upwards_trend: | `product`, `startup`, `saas`, `micro-saas`, `jtbd`, `jobs-to-be-done`, `customer`, `market`, `competitive`, `brand`, `persona`, `idea`, `darwin`, `personal tool` |
| **Finance** | :moneybag: | `finance`, `financial`, `trading`, `investment`, `buffett` |
| **Legal** | :scales: | `legal`, `law`, `contract`, `compliant`, `jurid`, `direito`, `advogado`, `criminal`, `trabalhista`, `tributario`, `consumidor`, `imobiliario`, `civil`, `leilao`, `leilões`, `edital`, `nulidades`, `cpc`, `lei` |
| **Compliance** | :scroll: | `compliance`, `audit`, `access review`, `pci`, `policy` |
| **Logistics** | :package: | `logistics`, `freight`, `carrier`, `returns`, `reverse logistics` |
| **Procurement** | :shopping_cart: | `procurement`, `purchase`, `energy procurement` |
| **Billing** | :credit_card: | `billing`, `invoice` |
| **Payments** | :dollar: | `payment`, `paypal`, `stripe`, `tax` |
| **ERP** | :office: | `odoo`, `erp`, `timesheet` |
| **Human Resources** | :busts_in_silhouette: | `employment`, `hr`, `payroll` |
| **Inventory** | :department_store: | `inventory`, `demand planning`, `warehouse` |
| **Manufacturing** | :factory: | `production scheduling`, `manufacturing` |
| **Careers** | :briefcase: | `interview`, `job search`, `resume`, `career` |

#### Quality & Data (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Security** | :shield: | `security`, `hack`, `vulnerability`, `pentest`, `penetration`, `auth`, `xss`, `threat`, `risk`, `attack`, `red team`, `active directory`, `kerberos`, `forensics`, `incident response`, `privilege escalation`, `secrets`, `credentials`, `mtls`, `zero-trust`, `shodan` |
| **Testing** | :test_tube: | `test`, `testing`, `qa`, `e2e`, `playwright`, `cypress`, `jest`, `tdd`, `validation`, `acceptance`, `verify` |
| **Debugging** | :beetle: | `debug`, `debugging`, `error`, `stack traces`, `bug`, `error detective`, `logs`, `root cause` |
| **Performance** | :racehorse: | `performance`, `performance bottlenecks`, `performance optimizer`, `profiling` |
| **Observability** | :telescope: | `observability`, `monitor`, `monitoring`, `prometheus`, `slo`, `tracing`, `jaeger`, `tempo` |
| **Code Quality** | :broom: | `technical debt`, `legacy`, `modernizer`, `refactor`, `clean code`, `code quality` |
| **Linting** | :sparkles: | `shellcheck`, `linting`, `lint` |
| **Quality Control** | :gem: | `quality control`, `non-conformance` |
| **Migration** | :airplane_departure: | `migration`, `code migration`, `framework migration` |
| **Analytics** | :bar_chart: | `analytics`, `backtesting`, `spreadsheet`, `xlsx` |
| **Data** | :ice_cube: | `data`, `vector`, `warehouse`, `forecast`, `analysis`, `analyze` |
| **Databases** | :file_cabinet: | `sql`, `postgres`, `mysql`, `database`, `dbt` |

#### Content & Knowledge (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Content** | :memo: | `content`, `writing`, `blog`, `article`, `video`, `audio`, `gif`, `favicon`, `unsplash`, `remotion`, `portfolio`, `rsvp`, `speed reader` |
| **Documentation** | :books: | `documentation`, `docs`, `readme`, `wiki`, `onboarding`, `obsidian`, `markdown`, `latex`, `paper`, `docx`, `pptx`, `office`, `document` |
| **Knowledge Management** | :bulb: | `summarizer`, `explain`, `socratic`, `bullet`, `knowledge`, `context`, `context save`, `context restore`, `diary`, `logger` |
| **Diagrams** | :world_map: | `mermaid`, `diagram` |
| **Design** | :art: | `design`, `canvas`, `canva`, `art`, `figma`, `theme`, `visual`, `hig`, `human interface guidelines` |
| **Communications** | :e-mail: | `communication`, `communication mode`, `internal comms`, `communications`, `brief`, `terse`, `caveman`, `status reports` |
| **Social Media** | :speech_balloon: | `social`, `twitter`, `youtube`, `publisher`, `x/twitter` |
| **Localization** | :earth_americas: | `i18n`, `localization`, `translation`, `locale`, `rtl` |

#### Specialized & Lifestyle (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Psychology** | :jigsaw: | `psychology`, `psychologist`, `identity`, `trust`, `calibrator`, `assumption`, `auditor`, `first-principles`, `emotional arc`, `loss aversion`, `objection`, `pitch`, `scarcity`, `urgency`, `sequence` |
| **Health** | :stethoscope: | `health`, `medical`, `clinical`, `hospital`, `emergency`, `medical card`, `goal analyzer`, `健康`, `医疗`, `急救` |
| **Mental Health** | :lotus_position: | `mental health`, `心理` |
| **Fitness** | :weight_lifter: | `fitness`, `nutrition`, `weightloss`, `营养` |
| **Sleep** | :crescent_moon: | `sleep`, `睡眠` |
| **Rehabilitation** | :adhesive_bandage: | `rehabilitation`, `康复` |
| **Traditional Medicine** | :herb: | `tcm`, `体质` |
| **Occupational Health** | :construction_worker: | `occupational health` |
| **Oral Health** | :tooth: | `oral health`, `口腔` |
| **Sexual Health** | :hospital: | `sexual health` |
| **Travel Health** | :airplane: | `travel health` |

#### System & Workflow (Main Category)
| Category | Emoji | Trigger Keywords |
| :--- | :---: | :--- |
| **Core Workflow** | :arrows_counterclockwise: | `plan`, `planning`, `brainstorm`, `brainstorming`, `constructive work`, `kaizen`, `essential`, `questions`, `underspecified`, `verification`, `completion`, `task`, `workflow`, `conductor`, `build`, `project guidelines`, `sharp edges`, `speckit`, `updater` |
| **Uncategorized** | :file_folder: | (Default fallback) |

---

## UI Implementation Details

### 1. Special Sections (Hardcoded Identifiers)
The `SkillModel` and QML layer recognize several "system" sections that bypass standard category logic:

| Section | Header Emoji | Item Icon | Description |
| :--- | :---: | :---: | :--- |
| **Starred** | :star: | :star: | High-priority skills (pinned to top). Golden tinted header. |
| **Collections** | :package: | :package: | Bundled skill sets (custom collections). |
| **Custom Commands** | :zap: | :zap: | Specialized executable skills. |

### 2. Supported Aliases
The `get_category_emoji()` logic supports common shorthand aliases for developer productivity:

- `Backend Dev` -> `Backend Development` (:gear:)
- `Web Dev` -> `Web Development` (:globe_with_meridians:)
- `Cloud Infra` -> `Cloud Infrastructure` (:cloud:)
- `Product Mgmt` -> `Product Management` (:chart_with_upwards_trend:)
- `Game Dev` -> `Game Development` (:video_game:)
- `Desktop Dev` -> `Desktop Development` (:desktop_computer:)
- `Knowledge Mgmt` -> `Knowledge Management` (:bulb:)
- `Mobile Dev` -> `Mobile Development` (:mobile_phone:)
- `Programming` -> `Programming Languages` (:keyboard:)

### 3. Collapsing & Sorting Logic (Two-Stage)
- **State Persistence**: Collapsed states for both Main Categories and Sub Categories are stored in the user configuration.
- **Section Sorting**:
  - Main Categories are sorted according to a predefined priority (System > Engineering > Business > Data > Knowledge > Lifestyle).
  - Sub Categories are sorted alphabetically within their Main Category.
  - **Starred**, **Collections**, and **Custom Commands** are forced to the top as pseudo-Main Categories.

---

## Developer Guide

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
1. **Define Logic**: Add the category and keywords to `CATEGORIES` in `src/skill_manager/core/parsing/constants.py`.
2. **Assign Visuals**: Update the mapping in `get_category_emoji()` in `src/skill_manager/core/categories.py`.
3. **Verify Sync**: Ensure `docs/CATEGORIES.md` matches the Python source.
