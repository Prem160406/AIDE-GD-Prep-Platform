from datetime import datetime

def generate_hr_questions(text, current_id_count):
    """
    Logic to transform a Job Role or Topic into an HR Interview Question set.
    """
    # 1. THE AI BRAIN (Prompt Logic)
    # In the future, this string will be sent to the Gemini API.
    # For now, we are simulating how the AI would split 'text' into questions.
    
    role_name = text.strip()
    
    # Mocking question generation based on the input role
    questions = [
        f"Why do you want to work as a {role_name}?",
        f"Describe a difficult technical challenge you faced in {role_name}.",
        "Where do you see yourself in 5 years?"
    ]
    
    # Combine questions into a single string or keep as list 
    # (Using a string for 'summary' to keep your current UI/DB compatible)
    formatted_questions = " | ".join(questions)

    # 2. THE DATA STRUCTURE
    # We keep the same keys so your 'app.py' and 'test_api.py' don't crash.
    new_topic = {
        "id": current_id_count + 1,
        "title": f"Interview: {role_name}", # Clearer title for HR project
        "summary": formatted_questions,    # This now holds the questions
        "source": "AI Generated",
        "source_url": "N/A",
        "source_name": "AIDE HR Coach",
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "issue_type": "HR Interview",      # Updated category
        "validation_score": 9,             # HR questions usually high priority
        "model_used": "gemini-1.5-flash",
        "prompt_version": "v2.0-hr-specialist"
    }
    
    return new_topic

