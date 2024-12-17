from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from Learner import AssessmentEngine, CurriculumGenerator, LessonGenerator
import secrets
import logging

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

assessment_engine = AssessmentEngine()
curriculum_generator = CurriculumGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_quiz():
    skill_level = request.form.get('skill_level')
    if skill_level not in ['Beginner', 'Intermediate', 'Advanced']:
        return redirect(url_for('index'))
    
    questions = assessment_engine.question_generator(skill_level)
    if not questions:
        return "Failed to generate questions. Please try again."
    
    session['skill_level'] = skill_level
    session['questions'] = questions
    session['current_question'] = 0
    session['user_responses'] = []
    
    return redirect(url_for('question'))

@app.route('/question')
def question():
    questions = session.get('questions', [])
    current_question = session.get('current_question', 0)
    
    if current_question >= len(questions):
        return redirect(url_for('results'))
    
    return render_template('question.html',question=questions[current_question],question_number=current_question + 1,total_questions=len(questions))

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    answer = request.form.get('answer')
    if not answer or answer not in ['a', 'b', 'c', 'd']:
        return redirect(url_for('question'))
    
    questions = session.get('questions', [])
    current_question = session.get('current_question', 0)
    user_responses = session.get('user_responses', [])
    
    user_responses.append(answer)
    session['user_responses'] = user_responses
    session['current_question'] = current_question + 1
    
    is_correct = answer == questions[current_question]['answer']
    return jsonify({
        'is_correct': is_correct,
        'correct_answer': questions[current_question]['answer'],
        'explanation': questions[current_question].get('explanation', '')
    })

@app.route('/results')
def results():
    questions = session.get('questions', [])
    user_responses = session.get('user_responses', [])
    
    results = assessment_engine.evaluate_user_responses(user_responses, questions)
    session['results'] = results
    
    return render_template('results.html', results=results)

@app.route('/curriculum')
def generate_curriculum():
    skill_level = session.get('skill_level')
    results = session.get('results')
    
    if not results:
        return redirect(url_for('index'))
    
    curriculum = curriculum_generator.generate_curriculum(skill_level, results['percentage'])
    if not curriculum:
        return "Failed to generate curriculum. Please try again."
    
    session['curriculum'] = curriculum
    return render_template('curriculum.html', curriculum=curriculum)

@app.route('/lessons')
def lessons():
    curriculum = session.get('curriculum')
    if not curriculum:
        return redirect(url_for('index'))
    
    lesson_generator = LessonGenerator(curriculum)
    key_topics = curriculum.get('key_topics', [])
    
    lessons_content = []
    for topic in key_topics:
        topic_name = topic.get('topic_name')
        lesson = lesson_generator.generate_lesson(topic_name)
        lessons_content.append({
            'title': topic_name,
            'content': lesson,
            'subtopics': topic.get('subtopics', [])
        })
    
    return render_template('lessons.html', lessons=lessons_content)

@app.route('/follow_up/<topic_name>')
def follow_up_questions(topic_name):
    curriculum = session.get('curriculum')
    if not curriculum:
        return redirect(url_for('index'))
    
    lesson_generator = LessonGenerator(curriculum)
    lesson = lesson_generator.generate_lesson(topic_name)
    
    return render_template('follow_up.html', topic=topic_name,lesson=lesson)

if __name__ == '__main__':
    app.run(debug=True)