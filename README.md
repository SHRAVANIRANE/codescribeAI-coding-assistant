# ðŸš€ CodeScribeAI

ðŸš§ Note: The Project is in development
<br>
**CodeScribeAI** is an AI-powered coding assistant that helps you **explore, debug, and understand code** effortlessly.  
Built with **React**, **Node.js**, and **Ollama LLM**, itâ€™s designed to boost developer productivity and make coding more intuitive.  

---

## âœ¨ Features

- ðŸ¤– **AI-Powered Assistance** â€“ Get instant explanations, debugging help, and code insights.  
- ðŸ“‚ **File Analysis** â€“ Upload or select files for detailed breakdowns.  
- ðŸ’¡ **Smart Suggestions** â€“ Improve your code with AI-driven recommendations.  
- ðŸŽ¨ **Clean UI** â€“ Minimal and distraction-free interface built with React + Tailwind.  
- ðŸ› ï¸ **Extensible Backend** â€“ Node.js + Express API with modular routes.  
- ðŸ”’ **In Progress** â€“ Actively being developed with new features coming soon!  

---

## ðŸ› ï¸ Tech Stack

**Frontend**  
- âš›ï¸ React  
- ðŸŽ¨ Tailwind CSS  
- ðŸ”„ React Router  
- âœ¨ GSAP (animations)  

**Backend**  
- ðŸŸ¢ Node.js + Express  
- ðŸ—„ï¸ MySQL2 (with SSL for DigitalOcean)  
- ðŸ“¦ Multer (file uploads)  
- ðŸ“§ Nodemailer (email handling)  

**AI**  
- ðŸ§  [Ollama](https://ollama.ai) â€“ Local LLM integration  

---

## ðŸš€ Getting Started

Follow these steps to set up CodeScribeAI locally:

### 1ï¸âƒ£ Clone the Repository
```bash
git clone https://github.com/your-username/codescribeAI.git
cd codescribeAI
```
### 2ï¸âƒ£ Install Dependencies
```bash
Frontend:
cd frontend
npm install
Backend:
cd backend
npm install
```
### 3️⃣ Configure Environment
Copy `.env.example` to `.env` and fill values:
```bash
cp .env.example .env
```
Required values:
```bash
APP_ENV=development
SECRET_KEY=replace-with-a-long-random-string
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_TOKEN=your_github_token
OLLAMA_URL=http://127.0.0.1:11434
```
Security notes:
- Never commit `.env` to git.
- Rotate secrets immediately if they were ever shared.
### 4ï¸âƒ£ Run the Project
Start backend:
```bash
cd backend
npm run dev
Start frontend:
cd frontend
npm run dev
```

---

## ðŸ“Œ Roadmap
 AI-powered debugging suggestions

 Multi-file context awareness

 Chat-like interface for conversations with AI

 Cloud deployment (Vercel + DigitalOcean)

 Authentication & user profiles

## ðŸ¤ Contributing
Contributions are welcome!

Fork the repo

Create a feature branch (git checkout -b feature-name)

Commit changes (git commit -m "Add feature")

Push to your branch (git push origin feature-name)

Open a Pull Request ðŸŽ‰

## ðŸ“œ License
This project is licensed under the MIT License.
See the LICENSE file for details.

## ðŸŒŸ Support
If you like this project, please consider giving it a â­ on GitHub â€“ it helps a lot!

## ðŸ“¸ Screenshots (Coming Soon)


