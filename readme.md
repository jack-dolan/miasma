# Miasma - Personal Data Poisoning Service

A defensive data poisoning platform that helps individuals protect their privacy by strategically introducing misleading information into commercial data broker networks.

## Project Goals

- **Privacy Protection**: Reduce the accuracy of personal data held by commercial data aggregators
- **Learning Platform**: Modern full-stack development with industry-standard tools and practices - using this as a learning side-project
- **Personal Use First**: Initially single-user (me), with potential for future expansion

## Tech Stack

### Frontend
- **React 18** - Modern component-based UI
- **Tailwind CSS** - Utility-first styling
- **Vite** - Fast build tool and dev server
- **React Query** - Server state management

### Backend
- **Python 3.13** - Core language
- **FastAPI** - High-performance async web framework
- **PostgreSQL** - Primary database for campaigns and results
- **Redis** - Caching and session management
- **SQLAlchemy** - ORM with async support

### Data Collection & Processing
- **Selenium** - Web automation and scraping
- **BeautifulSoup4** - HTML parsing, plus the website art is pretty
- **Requests** - HTTP client for APIs
- **Pandas** - Data manipulation and analysis

### Infrastructure & DevOps
- **Docker** - Containerization
- **Docker Compose** - Local development environment
- **AWS ECS** - Container orchestration
- **AWS RDS** - Managed PostgreSQL
- **AWS ElastiCache** - Managed Redis
- **GitHub Actions** - CI/CD pipeline
- **Snyk** - Security vulnerability scanning

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React SPA     │────│   FastAPI       │────│   PostgreSQL    │
│   (Frontend)    │    │   (Backend)     │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌──────┴──────┐
                       │    Redis    │
                       │  (Caching)  │
                       └─────────────┘
```

## Features (Planned)

### Phase 1: Core Infrastructure
- [ ] User authentication and profile management
- [ ] Data source discovery and monitoring
- [ ] Basic web scraping for personal data lookup

### Phase 2: Intelligence Gathering
- [ ] Automated scanning of major data broker sites
- [ ] Data source mapping and classification
- [ ] Personal data inventory and tracking

### Phase 3: Data Injection
- [ ] Fictitious data generation algorithms
- [ ] Automated form submission system
- [ ] Campaign management and tracking

### Phase 4: Verification & Analytics
- [ ] Success rate monitoring
- [ ] Data propagation tracking
- [ ] Effectiveness analytics dashboard

## Privacy & Legal Considerations

- **Scope Limitation**: Only targets commercial data brokers and voluntary submission sites
- **Government Exclusion**: Explicitly avoids interaction with official government sources
- **Personal Use**: Designed for individuals protecting their own data
- **Compliance**: Respects terms of service and applicable laws

## Quick Start

```bash
# Clone the repository
git clone https://github.com/jack-dolan/miasma.git
cd miasma

# Start development environment
docker-compose up -d

# Frontend development
cd frontend
npm install
npm run dev

# Backend development
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Development Workflow

1. **Feature Branch**: Create feature branches from `main`
2. **Development**: Use Docker Compose for local development
3. **Testing**: Automated testing with pytest and Jest
4. **Security**: Snyk scanning in CI pipeline
5. **Deployment**: Automated deployment to AWS via GitHub Actions

## Disclaimer

This tool is designed for legitimate privacy protection purposes. Users are responsible for ensuring their use complies with all applicable laws and terms of service.