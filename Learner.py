import json
import re
import logging
from typing import List, Dict, Optional
import groq


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AssessmentEngine:
    def __init__(self) -> None:
        self.api_key = self._get_api_key()
        self.client = groq.Client(api_key=self.api_key)

    @staticmethod
    def _get_api_key() -> str:
        api_key = 'your api Key'
        if not api_key:
            raise ValueError("API key not found. Please set the GROQ_API_KEY environment variable.")
        return api_key

    def get_user_level(self) -> str:
        valid_levels = {'a': 'Beginner', 'b': 'Intermediate', 'c': 'Advanced'}
        while True:
            skill_level = input("Enter Your Skill Level (a: Beginner, b: Intermediate, c: Advanced): ").strip().lower()
            if skill_level in valid_levels:
                return valid_levels[skill_level]
            logger.warning("Invalid input. Please enter a, b, or c.")

    def question_generator(self, skill_level: str) -> Optional[List[Dict]]:
        """
        Generate multiple-choice questions using the Groq API.

        Args:
            skill_level (str): The user's skill level.

        Returns:
            Optional[List[Dict]]: A list of questions with options and correct answers, or None if an error occurs.
        """
        try:
            logger.info(f"Generating questions for {skill_level} level...")
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{
                    "role": "user",
                    "content": f"Generate 10 multiple-choice questions on the Hindi Language for {skill_level} level. Each question should have 4 options (a, b, c, d) and include the correct answer. Format the output as a JSON array of objects with keys: 'text' for the question, 'choices' for options, and 'answer' for the correct answer."
                }],
                temperature=0
            )
            logger.info("Received response from API.")
            logger.debug(f"Raw API response: {response.choices[0].message.content}")
            try:
                questions = json.loads(response.choices[0].message.content)
                if not isinstance(questions, list):
                    logger.error("API response is not a JSON array as expected.")
                    return None
                return questions
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Raw content causing the error: {response.choices[0].message.content}")
                return None
        
        except groq.GroqError as e:
            logger.error(f"Error making API request: {e}")
            return None

    def collect_user_responses(self, questions: List[Dict]) -> List[str]:
        user_responses = []
        for i, q in enumerate(questions, 1):
            print(f"\nQuestion {i}: {q['text']}")
            for option, text in q['choices'].items():
                print(f"{option}) {text}")
            
            while True:
                answer = input("Your Answer (a/b/c/d): ").strip().lower()
                if answer in ['a', 'b', 'c', 'd']:
                    user_responses.append(answer)
                    if answer == q['answer']:
                        print("Correct!")
                    else:
                        print(f"Incorrect. The correct answer was {q['answer']}.")
                    break
                else:
                    logger.warning("Invalid Input. Please enter a, b, c, or d.")
        return user_responses
    
    def evaluate_user_responses(self, user_responses: List[str], questions: List[Dict]) -> Dict[str, float]:
        if not questions:
            return {"score": 0, "total_questions": 0, "percentage": 0.0}

        correct_count = sum(1 for user_answer, question in zip(user_responses, questions)
                            if user_answer == question.get("answer"))

        total_questions = len(questions)
        percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

        return {
            "score": correct_count,
            "total_questions": total_questions,
            "percentage": round(percentage, 2)
        }

class CurriculumGenerator:
    def __init__(self):
        self.assessment_engine = AssessmentEngine()
        self.api_key = self.assessment_engine._get_api_key() 
        self.client = groq.Client(api_key=self.api_key)

    def generate_curriculum(self, skill_level: str, evaluation_score: float, language: str = "Hindi") -> Optional[Dict]:
        """
        Generate a curriculum based on the user's skill level and evaluation score.
        """
        try:
            logger.info(f"Generating curriculum for {skill_level} level with score {evaluation_score}% in {language}")
            
            prompt = f"""
            Generate a curriculum for a {skill_level} level student in {language} language.
            The student scored {evaluation_score}% in their assessment.
            Create a structured curriculum with the following components:
            1. Learning Objectives
            2. Key topics (with subtopics)-make sure to include this under a 'key_topics' field
            3. Recommended Resources (books, websites, apps)
            4. Practice Exercises
            5. Assessment Methods

            Format the output as a JSON object with these main keys, including key_topics.
            Ensure the curriculum is tailored to the student's performance and skill level.
            """

            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            logger.info("Received curriculum from API.")
        
            content = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    curriculum = json.loads(json_str)
                    curriculum['skill_level'] = skill_level  # Add skill level here
                    return curriculum
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing extracted JSON: {e}")
                    logger.error(f"Extracted JSON causing the error: {json_str}")
                    return None
            else:
                logger.error("No JSON object found in the response")
                return None

        except groq.GroqError as e:
            logger.error(f"Error making API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in generate_curriculum: {e}")
            return None

class LessonGenerator:
    
    def __init__(self, curriculum: Dict, language: str = "Hindi"):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing LessonGenerator...")

        self.curriculum = curriculum
        self.language = language
        self.api_key = AssessmentEngine._get_api_key()
        self.client = groq.Client(api_key=self.api_key)
        self.logger.info(f"LessonGenerator initialized with language: {self.language}")

    def generate_lesson(self, key_topic: str) -> str:
        self.logger.info(f"Generating lesson for topic: {key_topic}")
        

        subtopics = self.get_subtopics(key_topic)
        
        prompt = f"""
        Generate a theory lesson for the topic '{key_topic}' in {self.language}.
        The lesson should cover the following subtopics:
        {', '.join(subtopics)}

        The lesson should:
        1. Introduce the main topic
        2. Explain each subtopic in detail
        3. Provide examples for each concept
        4. Include a summary at the end

        Format the lesson in Markdown, with clear headings, subheadings, and bullet points where appropriate.
        Ensure the content is suitable for the {self.curriculum['skill_level']} skill level.
        """

        try:
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            lesson = response.choices[0].message.content
            self.logger.info(f"Lesson generated for topic: {key_topic}")
            return lesson
        except Exception as e:
            self.logger.error(f"Error generating lesson for topic {key_topic}: {e}")
            return "Error generating lesson."

    def get_subtopics(self, key_topic: str) -> List[str]:
        """_summary_

        Args:
            key_topic (str): _description_

        Returns:
            List of topics
        """
        key_topics = self.curriculum.get('key_topics', [])
        for topic in key_topics:
            if topic.get('topic_name') == key_topic:
                return topic.get('subtopics', [])
    
        self.logger.error(f"No subtopics found for topic: {key_topic}")
        return []


        
    def ask_follow_up_questions(self, lesson: str, key_topics: str) -> None:
        """
        Handle lesson progression and offer options to the user.
        
        Args:
            lesson (str): The lesson content (can be empty string)
            key_topics (List[Dict] or List[str]): List of topics to cover
        """
        # If key_topics is a list of dictionaries, extract topic names
        if key_topics and isinstance(key_topics[0], dict):
            key_topics = [topic['topic_name'] for topic in key_topics]
        
        self.completed_lessons = []
        current_lesson = 0
        
        while current_lesson < len(key_topics):
            key_topic = key_topics[current_lesson]
            print(f"\nStarting lesson on: {key_topic}")
            lesson = self.generate_lesson(key_topic)
            print(lesson)
            
            # Ask follow-up questions about the lesson
            prompt = f"""
            Based on the following lesson about {key_topic}, generate 3 follow-up questions to assess the user's understanding.
            For each question, provide:
            1. The question
            2. The correct answer
            3. An explanation of the concept behind the answer
            4. A recommendation for further study if the user answers incorrectly

            Lesson content:
            {lesson}

            Format the output as a JSON array of objects, where each object has the keys:
            "question", "correct_answer", "explanation", "study_recommendation"
            """

            try:
                response = self.client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                questions = json.loads(response.choices[0].message.content)
            except Exception as e:
                self.logger.error(f"Error generating follow-up questions: {e}")
                return

            print("\nFollow-up Questions for this lesson:")
            for q in questions:
                print(f"\n{q['question']}")
                user_answer = input("Your answer: ").strip()
            
            if user_answer.lower() != q['correct_answer'].lower():
                print(f"Your answer is incorrect. The correct answer is: {q['correct_answer']}")
                print(f"Explanation: {q['explanation']}")
                print(f"To strengthen this point, you should: {q['study_recommendation']}")
                
                # Generate a more focused follow-up question on the misunderstood concept
                focused_prompt = f"""
                The user didn't understand the concept related to this question:
                "{q['question']}"
                
                Generate a more focused follow-up question to help clarify the concept.
                Provide the question, correct answer, and a brief explanation.
                """
                
                try:
                    focused_response = self.client.chat.completions.create(
                        model="mixtral-8x7b-32768",
                        messages=[{"role": "user", "content": focused_prompt}],
                        temperature=0.2
                    )
                    focused_question = json.loads(focused_response.choices[0].message.content)
                    
                    print("\nLet's try a more focused question to clarify this concept:")
                    print(focused_question['question'])
                    focused_answer = input("Your answer: ").strip()
                    
                    if focused_answer.lower() != focused_question['correct_answer'].lower():
                        print(f"The correct answer is: {focused_question['correct_answer']}")
                        print(f"Explanation: {focused_question['explanation']}")
                    else:
                        print("Correct! Great job on understanding the concept better.")
                except Exception as e:
                    self.logger.error(f"Error generating focused follow-up question: {e}")
            else:
                print("Correct! Well done.")    
            """
            Handle lesson progression and offer options to the user.
            """
            current_lesson = 0
            
            while current_lesson < len(key_topics):
                key_topic = key_topics[current_lesson]
                print(f"\nStarting lesson on: {key_topic}")
                lesson = self.generate_lesson(key_topic)
                print(lesson)
                
                # After the lesson, ask follow-up questions and provide feedback
                self.ask_follow_up_questions(lesson, key_topic)
                
                # Track completed lesson
                self.completed_lessons.append(key_topic)
                
                # Ask the user if they want to continue
                while True:
                    next_step = input("\nDo you want to (n)ext lesson, (r)epeat this lesson, or (q)uit? ").strip().lower()
                    if next_step == 'n':
                        current_lesson += 1
                        break
                    elif next_step == 'r':
                        break  # Repeat the current lesson
                    elif next_step == 'q':
                        print("Exiting the lesson sequence. Thank you!")
                        return
                    else:
                        print("Invalid input. Please enter 'n', 'r', or 'q'.")

            print("Congratulations! You have completed all the lessons.")

def main():
    engine = AssessmentEngine()

    # Step 1: Get the user's skill level
    skill_level = engine.get_user_level()

    # Step 2: Generate questions based on user level
    questions = engine.question_generator(skill_level)
    if questions is None:
        logger.error("Failed to generate questions.")
        return

    # Step 3: Collect user responses to the questions
    user_responses = engine.collect_user_responses(questions)

    # Step 4: Evaluate the user's responses
    results = engine.evaluate_user_responses(user_responses, questions)
    logger.info(f"User Score: {results['score']} out of {results['total_questions']} ({results['percentage']}%)")

    # Step 5: Generate curriculum based on results
    curriculum_generator = CurriculumGenerator()
    curriculum = curriculum_generator.generate_curriculum(skill_level, results['percentage'])

    if curriculum:
        logger.info("\nFull Curriculum Structure:")
        logger.debug("\nFull Curriculum Structure:")
        logger.info(json.dumps(curriculum, indent=4))
        logger.debug(json.dumps(curriculum, indent=4))
        
        # Extract topic names from the new curriculum structure
        key_topics = [topic['topic_name'] for topic in curriculum.get('key_topics', [])]
        
        logger.info(f"Extracted Key Topics: {key_topics}")
        
        # Step 6: Initiate lessons for the user
        lesson_generator = LessonGenerator(curriculum)
        
        if key_topics:
            # Modify this to pass key_topics to match your existing method signature
            lesson_generator.ask_follow_up_questions("", key_topics)
        else:
            logger.error("No key topics found in the curriculum. Unable to generate lessons.")
    else:
        logger.error("Failed to generate curriculum.")
        
if __name__ == '__main__':
    main()
