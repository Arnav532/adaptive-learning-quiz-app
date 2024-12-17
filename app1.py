from flask import Flask, render_template, request, redirect, url_for, session
import logging
from Learner import AssessmentEngine,CurriculumGenerator,LessonGenerator  
import secrets
import json

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

assessment_engine = AssessmentEngine()
curriculum_generator = CurriculumGenerator()


@app.route('/')
def index():
    """Homepage: Allows the user to select their skill level."""
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start_quiz():
    """Start the quiz based on the user's selected skill level."""
    skill_level = request.form.get('skill_level')
    if skill_level not in ['Beginner', 'Intermediate', 'Advanced']:
        return redirect(url_for('index'))
    
    # Save the skill level in the session
    session['skill_level'] = skill_level
    session['current_question'] = 0 
    session['user_responses'] = []  
    
    # Generate questions
    questions = assessment_engine.question_generator(skill_level)
    if not questions:
        return "Failed to generate questions. Please try again."
    
    session['questions'] = questions  # Save questions in the session
    return redirect(url_for('question'))


@app.route('/question')
def question():
    """Display the current question."""
    current_question = session.get('current_question', 0)
    questions = session.get('questions',[])
    
    if current_question >= len(questions):
        return redirect(url_for('results'))
    
    question = questions[current_question]
    return render_template('question.html', question=question, question_number=current_question + 1)


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Handle the user's answer and move to the next question."""
    answer = request.form.get('answer')
    current_question = session.get('current_question', 0)
    questions = session.get('questions', [])
    
    if answer not in ['a', 'b', 'c', 'd']:
        return redirect(url_for('question'))
    
    user_responses = session.get('user_responses', [])
    user_responses.append(answer)
    session['user_responses'] = user_responses
    
    session['current_question'] = current_question + 1
    return redirect(url_for('question'))


@app.route('/results')
def results():
    """Evaluate user responses and display the results."""
    questions = session.get('questions', [])
    user_responses = session.get('user_responses', [])
    
    results = assessment_engine.evaluate_user_responses(user_responses, questions)
    session['results'] = results
    
    return render_template('results.html', results=results)


@app.route('/curriculum')
def curriculumgenerator():
    skill_level = session.get('skill_level', 'Beginner')
    results = session.get('results', {})

    if not results:
        return redirect(url_for('index'))

    curriculum = curriculum_generator.generate_curriculum(skill_level, results['percentage'])

    if not curriculum:
        return "Failed to generate curriculum. Please try again."

    # Debug print to see the actual type and content of curriculum
    logger.info(f"Curriculum type: {type(curriculum)}")
    logger.info(f"Curriculum content: {curriculum}")

    # If curriculum is a string, try to parse it as JSON
    if isinstance(curriculum, str):
        try:
            curriculum = json.loads(curriculum)
        except json.JSONDecodeError:
            return f"Failed to parse curriculum. Received: {curriculum}"

    session['curriculum'] = curriculum
    return render_template('curriculum.html', curriculum=curriculum,skill_level=curriculum.get('skill_level', skill_level))
@app.route('/lessons')
def lessons():
    """Generate and display lessons based on the curriculum."""
    curriculum = session.get('curriculum', {})
    if not curriculum:
        return redirect(url_for('index'))
    
    lesson_generator = LessonGenerator(curriculum=curriculum)
    
    
    key_topics = curriculum.get('key_topics', [])
    
    if not key_topics:
        return "No topics found in the curriculum."
    
    # Generate lessons for each key topic
    lessons = []
    for topic in key_topics:
     if isinstance(topic, dict):
        topic_name = topic.get('topic_name', '')
     else:
        topic_name = topic
    
    lesson = lesson_generator.generate_lesson(topic_name)
    lessons.append({'title': topic_name, 'content': lesson})
    return render_template('lessons.html', lessons=lessons)


if __name__ == '__main__':
    app.run(debug=True)
