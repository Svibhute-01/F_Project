 <div align="center">

# 🚀 AI WORKFORCE

### Intelligent Software Development, Powered by Multi-Agent AI

**A Multi-Agent AI Platform for Intelligent Software Development Life Cycle Automation**

![Multi-Agent AI](https://img.shields.io/badge/AI-Multi--Agent%20System-6C63FF?style=for-the-badge)
![Software Engineering](https://img.shields.io/badge/Domain-Software%20Engineering-2563EB?style=for-the-badge)
![Final Year Project](https://img.shields.io/badge/Project-Final%20Year%20Project-0F766E?style=for-the-badge)

*From requirements to quality assurance — one intelligent workspace.*

</div>

---

## ✨ About the Project

**AI Workforce** is an intelligent multi-agent platform designed to support and automate key activities across the **Software Development Life Cycle (SDLC)**.

Software development involves several connected stages: understanding requirements, planning work, designing system architecture, implementing software, and validating its quality. Handling these activities independently can require significant time and coordination.

AI Workforce brings these responsibilities into one platform through **five specialized AI modules**. Each module focuses on a specific development activity and contributes to a more structured workflow.

The platform combines a web-based interface, backend services, AI-powered processing, and **Retrieval-Augmented Generation (RAG)** capabilities to support project-related work.

> **Our vision:** Make software development more organized and intelligent by bringing specialized AI assistance into a unified workspace.

## 🎯 The Problem

Traditional software development workflows can involve:

- Repetitive manual work across different SDLC stages.
- Time-consuming requirement analysis and documentation.
- Challenges in planning and coordinating project activities.
- Difficulty maintaining consistency between requirements, design, implementation, and testing.
- Separate tools and processes for different development responsibilities.

There is a need for an integrated solution that can assist teams throughout these connected activities.

## 💡 Our Solution

AI Workforce organizes software development assistance into five specialized AI modules:

| # | AI Module | Primary Responsibility |
|---|---|---|
| 01 | **Requirements Analyst AI** | Understands and structures project requirements |
| 02 | **Project Manager AI** | Supports planning, user stories, and task organization |
| 03 | **System Architecture AI** | Assists with system structure and architectural design |
| 04 | **Developer AI** | Supports software implementation and code-related work |
| 05 | **Quality Assurance AI** | Supports test preparation and quality validation |

Together, these modules cover important activities from initial requirement understanding to development and quality checks.

## 🌟 Platform Highlights

| Feature | What it offers |
|---|---|
| **Project Workspace** | Create and manage software development projects |
| **Document Management** | Upload and manage project documents, including SRS files |
| **Requirements Analysis** | Organize functional and non-functional requirements |
| **AI-Powered Planning** | Support user stories, sprint planning, and task organization |
| **Architecture Assistance** | Help structure system components and their relationships |
| **Developer Assistance** | Provide AI-powered support for implementation activities |
| **Quality Assurance** | Assist with test cases, edge cases, and quality checks |
| **Project Chat** | Interact with project-related functionality through chat |
| **Centralized Dashboard** | Access projects, documents, agents, and tasks in one place |
| **Reports & Settings** | Access available reporting and application configuration features |

## 🤖 Meet the AI Workforce

### 01 — Requirements Analyst AI
*Turning project ideas into structured requirements.*

The Requirements Analyst AI focuses on understanding what needs to be built.

- Analyzes the provided project description and requirements.
- Identifies functional requirements.
- Identifies non-functional requirements.
- Organizes requirements into a structured format.
- Supports the preparation of Software Requirements Specifications (SRS).

### 02 — Project Manager AI
*Bringing structure to project planning.*

The Project Manager AI supports the organization and coordination of project activities.

- Helps convert requirements into development activities.
- Organizes user stories.
- Supports sprint planning and backlog organization.
- Assists with task allocation and tracking.
- Helps structure the project workflow.

### 03 — System Architecture AI
*Shaping the technical blueprint.*

The System Architecture AI supports the design and architectural planning stage.

- Analyzes project requirements and planning information.
- Assists in identifying major system components.
- Supports the organization of the system structure.
- Helps describe relationships between system components.
- Provides architectural design assistance.

### 04 — Developer AI
*Supporting the journey from design to implementation.*

The Developer AI focuses on software development activities.

- Provides AI-powered development assistance.
- Supports code-related tasks.
- Assists with implementation activities.
- Helps developers work through software development requirements.

### 05 — Quality Assurance AI
*Supporting software testing and validation.*

The Quality Assurance AI focuses on software quality activities.

- Supports test-case preparation.
- Assists in identifying possible edge cases.
- Helps evaluate software functionality.
- Supports the software quality-checking process.

---

## 🏗️ System Architecture

AI Workforce follows a layered architecture in which the frontend, backend, AI services, knowledge retrieval, and data storage work together.

### Architecture Layers

| Layer | Responsibility |
|---|---|
| **Presentation Layer** | React.js interface for the dashboard, projects, documents, AI modules, and other application features |
| **Backend Layer** | Handles application requests, business logic, project operations, and communication with AI services |
| **AI Processing Layer** | Hosts specialized AI modules for requirements, planning, architecture, development, and quality assurance |
| **Knowledge Retrieval Layer** | Uses RAG to retrieve relevant project information when required and provide context to AI workflows |
| **Data Layer** | Supports storage and retrieval of application and project information; SQLite is used as a fallback when `DATABASE_URL` is not configured |

### High-Level Workflow

<img width="1002" height="494" alt="image" src="https://github.com/user-attachments/assets/04bbb0d9-5adb-4cd8-90f9-580d5a0323c5" />


## 🔄 How the Platform Works

1. **Create a project** — The user creates a software development project.
2. **Add project documents** — Relevant documents, such as an SRS, can be uploaded.
3. **Analyze requirements** — Requirements Analyst AI helps organize project requirements.
4. **Plan the work** — Project Manager AI supports planning and task organization.
5. **Design the system** — System Architecture AI assists with architectural planning.
6. **Support development** — Developer AI assists with implementation-related activities.
7. **Validate quality** — Quality Assurance AI supports testing and validation.
8. **Manage the project** — Users access available project information and management features through the dashboard.

## 🧰 Technology Stack

| Area | Technology |
|---|---|
| Frontend | React.js |
| Frontend Build Tool | Vite |
| Backend Services | Python, FastAPI |
| AI Approach | Multi-Agent AI |
| Knowledge Retrieval | Retrieval-Augmented Generation (RAG) |
| Database | SQLite fallback; database configuration supported through `DATABASE_URL` |
| API Communication | REST APIs |
| Development Environment | Visual Studio Code |
| Version Control | Git and GitHub |

*The exact LLM provider, model configuration, and additional infrastructure depend on the configured environment.*

## 📁 Repository Structure

The repository contains the main AI Workforce application and a separate Developer Agent component.

```text
AI-WorkForce/
│
├── AI_Workforce/
│   ├── Frontend/
│   │   └── React.js and Vite application
│   │
│   ├── Backend/
│   │   └── FastAPI application and AI services
│   │
│   └── Project-related modules and resources
│
├── Developer_Agent/
│   └── Developer Agent implementation
│
└── README.md
```

*This is a simplified overview. Refer to the repository for the exact folder and file organization.*

## ⚙️ Getting Started

> **Note:** The commands below reflect the development setup. Confirm the actual entry-point files, dependency files, and service configuration in the repository before running them.

### Prerequisites

- Python 3.10 or later, subject to the project's dependency requirements.
- Node.js and npm.
- Git.
- Visual Studio Code (recommended).

### 1. Clone the Repository

```bash
git clone https://github.com/Saniya2701/AI-WorkForce.git
cd AI-WorkForce
```

### 2. Set Up the Main Python Application

```bash
cd AI_Workforce
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies if a `requirements.txt` file is present in this directory:

```bash
pip install -r requirements.txt
```

Start the backend using the configured application entry point. For example, if the entry point is `main.py` and exposes `app`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

The example local address is:

```text
http://127.0.0.1:8000
```

### 3. Set Up the Developer Agent

Open a **separate terminal**, navigate to the `Developer_Agent` directory, and activate its Python environment.

Install its dependencies using the requirements file provided in that directory, if present. Start the service using its configured entry point.

The development setup has used the following local address for this service:

```text
http://127.0.0.1:8001
```

### 4. Set Up the Frontend

Open another terminal and navigate to the frontend directory containing `package.json`.

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npx vite --port 5000
```

Open the frontend in your browser:

```text
http://localhost:5000
```

**Keep each required service running in its own terminal while using the application.** If your repository uses different scripts, ports, or entry points, follow its actual configuration.

## 🔐 Environment Configuration

Some features may require environment variables or external AI service configuration.

Before running the application:

1. Check for `.env.example` or other environment documentation in the repository.
2. Configure the required API keys and service URLs locally.
3. Configure the database connection if required.
4. Keep credentials and private configuration out of Git.

The backend supports SQLite as a fallback when `DATABASE_URL` is not configured.

> **Security reminder:** Never commit real API keys, passwords, access tokens, or private `.env` files to GitHub.

## 🎯 Project Objectives

- Develop an integrated multi-agent AI platform for SDLC automation.
- Divide software development responsibilities among specialized AI modules.
- Reduce repetitive manual effort in software development activities.
- Support structured requirement analysis and project planning.
- Assist in system architecture design and development.
- Support software testing and quality assurance.
- Provide a centralized interface for project-related activities.

## ✅ Advantages

- Organizes multiple stages of software development in one platform.
- Provides specialized AI assistance for different SDLC activities.
- Supports structured requirement analysis and project planning.
- Helps keep project-related information accessible.
- Demonstrates practical applications of Multi-Agent Systems and RAG.

## 🔭 Future Scope

The platform can be extended through:

- Integration with additional LLM providers and models.
- More advanced agent-to-agent coordination.
- Improved RAG pipelines and knowledge management.
- Integration with GitHub repositories and development workflows.
- Automated code execution and testing environments.
- Advanced project analytics and reporting.
- Role-based access control and enhanced security.
- Deployment as a scalable cloud-based application.

## 🖥️ Screenshots & Demonstration

| Screenshot 1 | Screenshot 2 |
|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/b3b84be8-f480-4376-a359-32cd0d9918fa" width="450"> | <img src="https://github.com/user-attachments/assets/dc1466d5-df9b-40ae-b11a-b51bf7a7f263" width="450"> |
| <img src="https://github.com/user-attachments/assets/8e0e28b9-7559-408c-825a-5c979a6486cb" width="450"> | <img src="https://github.com/user-attachments/assets/1142c187-2df1-44aa-91ea-824ff20f3a55" width="450"> |
| <img src="https://github.com/user-attachments/assets/22968d9d-ba04-443d-935c-a2b0a8d19469" width="450"> | <img src="https://github.com/user-attachments/assets/96ec4c91-f09e-4027-bf42-4b3fe919b625" width="450"> |
| <img src="https://github.com/user-attachments/assets/243cf409-ab40-4792-8276-82de7c6dc44f" width="450"> | <img src="https://github.com/user-attachments/assets/9063f919-daf4-4756-89d5-3e3d1b98e7c6" width="450"> |

---








**Live Demonstration:** https://drive.google.com/file/d/1KlZzVV5_XdFPRHf4DZ66Rl7f7qfeKDT0/view?usp=sharing

## 👩‍💻 Project Team

**Department of Computer Science and Engineering**  
**D. Y. Patil College of Engineering and Technology, Kolhapur**

| Team Member |
|---|
| Saniya Mane |
| Snehal Vibhute |
| Shruti Konduskar
| Sayli Gurav |
| Vishal Chougale |

**Project Guide:** Mrs S. G. Ambi

## 🎓 Academic Context

AI Workforce was developed as a final-year academic project to explore the application of Artificial Intelligence, Multi-Agent Systems, and Retrieval-Augmented Generation in supporting software development life-cycle activities.


<div align="center">

### 💙 AI Workforce

**Making Software Development Smarter with Multi-Agent AI.**

*Built by the Computer Science and Engineering team at D. Y. Patil College of Engineering and Technology, Kolhapur.*

</div>
