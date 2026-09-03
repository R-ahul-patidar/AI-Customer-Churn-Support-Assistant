Developer Skill Test
Python + SQL + LangChain + GenAI + Machine Learning
Project: AI Customer Churn & Support Assistant
Objective
Build and deploy an end-to-end AI-powered customer analytics and support application. The candidate must
demonstrate practical skills in Python, SQL, Machine Learning, LangChain, GenAI, API development, and
deployment.
1. Dataset & SQL
Create or use a customer dataset containing at least: customer_id, age, plan, monthly_spend, tenure_months,
support_tickets, last_login_days, satisfaction_score, and churn.
• Store the data in PostgreSQL or MySQL.
• Write SQL queries for: top 10 customers by monthly spend; average spend by plan; customers with more than 5
support tickets; churn rate by plan; and customers with high churn-risk indicators.
2. Machine Learning
Build a customer churn prediction model using Python. The candidate may use Logistic Regression, Random Forest,
or XGBoost.
• Perform basic EDA and handle missing values.
• Perform feature engineering and train/test split.
• Evaluate using Accuracy, Precision, Recall, F1 Score, and ROC-AUC.
• Save the trained model and expose a prediction function/API.
Example API:
POST /predict-churn
Input: age, plan, monthly_spend, tenure_months, support_tickets, last_login_days, satisfaction_score.
Output: churn_probability and risk (LOW/MEDIUM/HIGH).
3. Python Backend
Build a FastAPI application with the following suggested endpoints:
Method Endpoint Purpose
GET /customers List/search customers
GET /customers/{customer_id} Customer details
GET /analytics Customer/churn analytics
POST /predict-churn Predict churn probability
POST /ask AI assistant query
4. LangChain + GenAI
Create an AI assistant that can answer questions about customer data. For example: “Why is customer C102 at high
risk of churn?”
1 Receive the user question.
2 Use LangChain to orchestrate retrieval and reasoning.
3 Retrieve relevant customer information from SQL.
4 Get the ML churn prediction.
5 Send relevant context to an LLM.
6 Generate a clear natural-language response with reasons and recommended action.
Bonus: Implement a SQL Agent / Text-to-SQL flow using LangChain so a user can ask questions such as “Which
plan has the highest churn rate?” and receive the SQL-backed answer.
5. Simple UI
• Use Streamlit or React.
• Dashboard: total customers, churn rate, average monthly spend, and high-risk customers.
• Customer Search: customer details and churn probability.
• AI Assistant: ask questions and display AI-generated answers.
6. Deployment — Mandatory
Deploy the complete working application publicly. AWS, Azure, GCP, Render, Railway, or another suitable platform
may be used.
Suggested architecture:
UI → FastAPI Backend → PostgreSQL + ML Model + LangChain → LLM
Required deliverables:
• Live application URL
• GitHub repository
• README with setup and architecture
• API documentation
• Database setup/schema script
• Dockerfile
•
.env.example
• ML training and prediction code
• Deployment instructions
Security: Never commit API keys, passwords, database credentials, or other secrets to GitHub.
7. Evaluation — 100 Marks
Area Marks
Python / FastAPI 20
SQL / Database 15
Machine Learning 20
LangChain 15
GenAI / Prompt Engineering 10
API Design 5
Deployment / Docker 10
Code Quality / README 5
TOTAL 100
8. Recommended Test Conditions
• Estimated effort: 6–8 hours
• Submission: Within 2 working days
• Experience level: 2–5 years
• Deployment: Mandatory
• Source control: GitHub repository required
9. Interview / Review Questions
1 Why did you select the ML algorithm you used?
2 Explain how your churn model works and how you evaluated it.
3 How does your application interact with the SQL database?
4 Explain your LangChain flow and where the LLM is used.
5 How does the AI assistant obtain customer context?
6 How did you deploy the application?
7 What happens from API request to final response?
8 How would you scale this application to 10,000+ users?
9 How did you handle secrets and environment variables?
10 What would you improve if this became a production system?
Final expectation: The candidate should submit a working, publicly accessible application—not only source code or
screenshots. The evaluator should be able to test the live application and review the GitHub repository.