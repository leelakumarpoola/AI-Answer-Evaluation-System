from app.database import SessionLocal
from app.services.document_extraction_service import extract_information
from app.services.student_answer_extraction_service import extract_student_answers
from app.services.semantic_similarity_service import calculate_semantic_similarity
from app.services.rubric_evaluation_service import evaluate_rubric
from app.services.feedback_service import generate_and_store_feedback
from app.models.student_answer import StudentAnswer

db = SessionLocal()

print('--- Extracting Exam 30 Master Documents ---')
extract_information(30, 19, db)
extract_information(30, 20, db)
extract_information(30, 21, db)

print('\n--- Evaluating Script 56 ---')
ext_res = extract_student_answers(56, db)
print('Segmentation method:', ext_res.get('extraction_method'))
print('Total answers extracted:', len(ext_res.get('answers', [])))

calculate_semantic_similarity(56, db)
rubric_res = evaluate_rubric(56, db)
print('Rubric evaluated results:', len(rubric_res))
for r in rubric_res:
    qid = r.get('question_id')
    marks = r.get('suggested_marks')
    max_m = r.get('max_marks')
    rev = r.get('needs_review')
    print(f'  Question {qid}: marks={marks}/{max_m}, needs_review={rev}')
    for c in r.get('criteria', []):
        crit = c.get('criterion')
        sm = c.get('suggested_marks')
        mm = c.get('max_marks')
        reason = c.get('reason')
        print(f'    - {crit}: {sm}/{mm} ({reason})')

answers = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == 56).all()
for a in answers:
    if a.evaluation:
        fb = generate_and_store_feedback(db, a.evaluation)
        print(f'  Feedback: {fb.feedback_text}')

print('\n--- Evaluating Script 57 ---')
ext_res57 = extract_student_answers(57, db)
calculate_semantic_similarity(57, db)
rubric_res57 = evaluate_rubric(57, db)
for r in rubric_res57:
    qid = r.get('question_id')
    marks = r.get('suggested_marks')
    max_m = r.get('max_marks')
    print(f'  Question {qid}: marks={marks}/{max_m}')

print('\nALL EVALUATIONS COMPLETED SUCCESSFULLY!')
