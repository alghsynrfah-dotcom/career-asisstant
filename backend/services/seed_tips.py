from backend.services.rag_service import save_tip

TIPS = [
    ("CV length and structure", "cv",
     "Keep a CV to one page for under 10 years of experience, two pages at most. "
     "Use a clear order: summary, skills, experience, projects, education. "
     "Put the most relevant information first and remove old or unrelated jobs."),

    ("Tailor your CV to the job posting", "cv",
     "Read the job posting and list its required skills and keywords. "
     "Reflect the real ones you have in your CV using the same wording, "
     "for example if the posting says REST APIs, write REST APIs. "
     "Never add skills you do not have."),

    ("Quantify your achievements", "cv",
     "Replace vague duties with measurable results. Instead of 'worked on the website', "
     "write 'built 5 pages that reduced load time by 30 percent'. "
     "Numbers such as users, time saved, percentages and team size make a CV convincing."),

    ("Use strong action verbs", "cv",
     "Start each bullet with a verb such as built, designed, led, improved, automated or delivered. "
     "Avoid phrases like 'responsible for' and 'helped with'. "
     "Keep each bullet to one or two lines."),

    ("Organize the skills section", "cv",
     "Group skills by category: programming languages, frameworks, databases, tools and languages spoken. "
     "List the skills the job asks for first. Do not rate skills with stars or percentages."),

    ("Projects section for juniors", "cv",
     "If you have little work experience, projects are your main proof. "
     "For each project write what it does, the technologies used, and your own role and result. "
     "Add a GitHub link when possible."),

    ("Make the CV ATS friendly", "cv",
     "Many companies use applicant tracking systems that scan the CV for keywords. "
     "Use simple formatting, standard headings, no tables, no images and no text boxes. "
     "Save the CV as PDF unless the posting asks for another format."),

    ("Write a professional summary", "cv",
     "Open the CV with two or three lines: your role, years or level of experience, "
     "your strongest skills, and the kind of position you want. "
     "Match it to the target job instead of using a generic sentence."),

    ("The STAR method for interview answers", "interview",
     "Structure behavioral answers as Situation, Task, Action, Result. "
     "Spend most of the time on what you did and the measurable result. "
     "Prepare four or five real stories that can fit many questions, such as a conflict, a failure, a deadline and a success."),

    ("Common behavioral questions", "interview",
     "Prepare answers for: tell me about yourself, why this company, your biggest strength and weakness, "
     "a time you failed, a time you disagreed with a teammate, and where you see yourself in five years. "
     "Practice them out loud, not only in your head."),

    ("Technical interview preparation", "interview",
     "Review the technologies listed in the posting and be ready to explain your own projects in depth. "
     "Practice explaining your thinking out loud while solving problems. "
     "If you do not know an answer, say what you would try instead of staying silent."),

    ("Tell me about yourself", "interview",
     "Answer in about one minute using present, past, future: what you do now, "
     "the experience that led you here, and why this role is the next step. "
     "Do not recite your whole CV or share personal details that are not relevant."),

    ("Questions to ask the interviewer", "interview",
     "Prepare three to five questions such as: what does success look like in the first six months, "
     "how is the team organized, and what are the biggest challenges of the role. "
     "Avoid asking about salary or vacation in the first interview unless they raise it."),

    ("Answering the weakness question", "interview",
     "Choose a real but non-critical weakness, explain what you are doing to improve it, "
     "and give a small example of progress. "
     "Avoid fake weaknesses like 'I work too hard'."),

    ("Salary negotiation basics", "career",
     "Research the market range for the role and your location before the conversation. "
     "Give a range instead of one number, and base it on your skills and results. "
     "Consider the whole package, including benefits, training and flexibility."),

    ("Follow up after the interview", "career",
     "Send a short thank-you email within 24 hours. "
     "Mention something specific from the conversation, repeat your interest in the role, "
     "and keep it to a few lines."),
]

for title, category, text in TIPS:
    result = save_tip(title=title, text=text, category=category)
    print(title, "->", result["chunks_saved"], "chunk(s)")

print("Done:", len(TIPS), "tips saved.")