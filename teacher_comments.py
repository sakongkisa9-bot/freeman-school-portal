"""Subject-specific CBC teacher comments and subject-to-comment assignments."""

RATING_ORDER = ("BE1", "BE2", "AE1", "AE2", "ME1", "ME2", "EE1", "EE2")

COMMENT_SETS = (
    {
        "BE1": "A starting point. Focus on understanding the basic concepts, and I am here to help you practice.",
        "BE2": "You are showing effort, but need more practice on the fundamentals to reach the expected level.",
        "AE1": "You are approaching the expected level. With more practice, you will master this.",
        "AE2": "Good effort shown. Keep working on the basics to build a stronger foundation.",
        "ME1": "Good progress. You are grasping the core ideas; continue practicing to gain more confidence.",
        "ME2": "Well done! You are very close to mastering this. Pay close attention to the finer details.",
        "EE1": "Great work! You have successfully demonstrated this competency. Keep up the consistent performance.",
        "EE2": "Outstanding! You have mastered the task and shown deep understanding. Keep challenging yourself.",
    },
    {
        "BE1": "The student is beginning to interact with the material but requires close guidance to grasp initial steps.",
        "BE2": "Steady effort is visible, though a stronger focus on primary rules will help unlock the next level.",
        "AE1": "Making noticeable strides toward the target. Reviewing recent lessons will solidify this progress.",
        "AE2": "Displays a promising rhythm. A bit more attention to foundational drills will yield great results.",
        "ME1": "Successfully meets the criteria. Demonstrates clear comprehension and applies methods correctly.",
        "ME2": "Commendable work. Shows a firm grip on the current topics with minimal errors.",
        "EE1": "Exemplary performance. Consistently produces high-quality work and thinks critically.",
        "EE2": "Superb mastery! Shows remarkable insight and independently explores advanced aspects of the course.",
    },
    {
        "BE1": "Initial attempts show potential, but regular review of basic vocabulary and definitions is essential.",
        "BE2": "Tries hard to follow instructions, but needs structured support to bridge the current learning gaps.",
        "AE1": "Moving in the right direction. Consolidating core knowledge will help clear up lingering doubts.",
        "AE2": "Gaining steady momentum. Refining daily study habits will help meet all criteria comfortably.",
        "ME1": "Competently handles classroom tasks. Displays a reliable understanding of all taught objectives.",
        "ME2": "Very good results. Shows great care in completing assignments accurately and effectively.",
        "EE1": "Superb dedication. Demonstrates a profound understanding and handles complex tasks with ease.",
        "EE2": "Exceptional talent and focus. Regularly produces flawless work and inspires peers during class.",
    },
    {
        "BE1": "Needs to establish a stronger routine in class to capture essential terminology and ideas.",
        "BE2": "Shows a willing attitude, but struggles to translate theoretical ideas into correct practical steps.",
        "AE1": "Getting closer to the benchmark. Extra focus on specific weak areas will yield a breakthrough.",
        "AE2": "Progressing well. A slight increase in focus during independent tasks will secure the goal.",
        "ME1": "Meets all learning targets. Actively participates and applies learned theories correctly.",
        "ME2": "Impressive work ethic. Demonstrates a highly secure and dependable understanding of the topic.",
        "EE1": "Stands out for detailed accuracy. Expresses solutions clearly and works with high autonomy.",
        "EE2": "Brilliant execution. Combines innovative thinking with complete mastery of the entire syllabus.",
    },
    {
        "BE1": "Requires intensive revision of foundational concepts to build confidence moving forward.",
        "BE2": "Participates gently but faces difficulty when applying basic formulas or core rules alone.",
        "AE1": "Approaching standard proficiency. Encouraging more active participation will boost performance.",
        "AE2": "Shows good instincts. Eliminating minor careless mistakes will help secure a higher level.",
        "ME1": "Performs reliably. Adequately grasps the subject matter and applies it to everyday examples.",
        "ME2": "Strong and steady progress. Consistently delivers neat, well-thought-out academic work.",
        "EE1": "Exceptional quality of work. Demonstrates advanced analytical skills and precise execution.",
        "EE2": "Remarkable insight! Displays a rare, natural aptitude and handles advanced content effortlessly.",
    },
    {
        "BE1": "Needs to prioritize the basics. I recommend regular remedial exercises to build core knowledge.",
        "BE2": "The student tries to keep up, but needs closer monitoring during independent study hours.",
        "AE1": "On the verge of meeting the standard. A more organized approach to revision will help.",
        "AE2": "Positive development is clear. Strengthening fundamental execution will bring total clarity.",
        "ME1": "Meets expectations well. Shows a healthy interest and handles core assignments with confidence.",
        "ME2": "Highly satisfactory output. Demonstrates a clear, well-rounded grasp of the subject areas.",
        "EE1": "Demonstrates superior capability. Consistently approaches academic challenges with high energy.",
        "EE2": "Flawless performance throughout. Exhibits deep intellectual curiosity and sophisticated skills.",
    },
    {
        "BE1": "Focusing on simple step-by-step listening will help build the groundwork required to proceed.",
        "BE2": "Attempts assignments willingly, but requires constant direction to remain on the right track.",
        "AE1": "Nearing the expected benchmark. More practice with textbook problems will build speed.",
        "AE2": "Developing nicely. Maintaining a steady work rate will bridge the remaining minor gaps.",
        "ME1": "Succeeds in proving competency. Work is organized, timely, and meets all curriculum criteria.",
        "ME2": "Very proficient. Shows an admirable ability to retain information and apply it correctly.",
        "EE1": "A standout learner. Demonstrates absolute precision and a creative approach to assignments.",
        "EE2": "Masterful performance. Shows an authoritative command over the material that goes beyond expectations.",
    },
    {
        "BE1": "Needs to cultivate a better grasp of the opening units before tackling more complex themes.",
        "BE2": "Requires patience and extra reinforcement at home to grasp core operational steps.",
        "AE1": "Advancing at a promising pace. Regular self-testing will help lock down expected skills.",
        "AE2": "Steady growth observed. Polishing up basic concepts will give a significant confidence boost.",
        "ME1": "Capable and efficient. Shows a complete understanding of all fundamental project work.",
        "ME2": "Exhibits a highly reliable skill set. Work is thoroughly researched and cleanly presented.",
        "EE1": "Remarkable dedication to excellence. Solutions are always well-crafted and insightful.",
        "EE2": "Outstanding achievements this term. Demonstrates a comprehensive, elite understanding of the subject.",
    },
    {
        "BE1": "Needs to re-read introductory notes carefully to grasp the vital building blocks of this area.",
        "BE2": "Showing good class attendance, but requires extra assistance to complete tasks independently.",
        "AE1": "Close to full understanding. Continual practice will turn minor struggles into strengths.",
        "AE2": "A very encouraging trend. Paying attention to small structural rules will elevate performance.",
        "ME1": "Satisfactory work across all units. Displays the essential skills required for this grade level.",
        "ME2": "High achievement shown. Grasps abstract concepts easily and works with great diligence.",
        "EE1": "Distinguished effort. Always goes above and beyond to provide thoroughly detailed answers.",
        "EE2": "Incredible mastery. Synthesizes complex ideas perfectly and shows exceptional academic leadership.",
    },
    {
        "BE1": "A fresh focus on simple drills and daily attention in class will yield better results.",
        "BE2": "Effort is there, but a tendency to rush results creates gaps in understanding key steps.",
        "AE1": "Approaching the desired learning targets. Keep working diligently on standard classroom exercises.",
        "AE2": "Solid progress. With a bit more practice on core procedures, standard goals will be fully met.",
        "ME1": "Competent and focused. Handles all learning objectives with a healthy degree of independence.",
        "ME2": "Very successful term. Clearly understands the nuances of the topics and solves tasks neatly.",
        "EE1": "Superb analytical skills. Frequently finds unique ways to solve complex curriculum problems.",
        "EE2": "Magnificent work. Demonstrates flawless retention and an incredibly mature grasp of the subject.",
    },
    {
        "BE1": "Grasping the basic terminology is the current priority. We will work closely on this together.",
        "BE2": "Struggles slightly with complex tasks, but shows a positive attitude toward receiving help.",
        "AE1": "Making good headway. Continued focus on structural elements will secure the required standard.",
        "AE2": "Moving forward beautifully. A small push in individual study time will lock in success.",
        "ME1": "Strong performance. Demonstrates a reliable capability to meet all expectations smoothly.",
        "ME2": "Very commendable progress. Answers are thoughtful, accurate, and submitted on time.",
        "EE1": "Consistently exceeds standard benchmarks. Shows great autonomy and academic pride.",
        "EE2": "Truly phenomenal. Displays a perfect command of the course and sets an excellent classroom example.",
    },
    {
        "BE1": "Needs to establish a clearer understanding of primary guidelines through deliberate revision.",
        "BE2": "Shows interest, but needs to slow down to properly absorb the core mechanics of the topic.",
        "AE1": "On track to hit the target. Just needs to apply consistent effort during group assignments.",
        "AE2": "An encouraging performance. Strengthening the basics will make advanced tasks much easier.",
        "ME1": "Well done. Shows a practical grasp of the subject matter and finishes tasks with confidence.",
        "ME2": "Highly proficient student. Handles coursework with great focus and delivers strong results.",
        "EE1": "Exemplary work throughout the term. Demonstrates clear, independent critical thinking.",
        "EE2": "Outstanding brilliance. Solves intricate problems with absolute ease and impeccable accuracy.",
    },
    {
        "BE1": "Targeted practice on the first few chapters will provide the momentum needed to catch up.",
        "BE2": "Willing to learn, but requires regular one-on-one interventions to master standard goals.",
        "AE1": "Steadily narrowing the gap to the expected level. Consistency is the key to full mastery now.",
        "AE2": "Shows a great foundational setup. A little more precision during tests will bring top marks.",
        "ME1": "Perfectly meets expectations. Displays a clear understanding and can work without supervision.",
        "ME2": "Strong academic output. Demonstrates great focus, turning out consistently high-quality work.",
        "EE1": "A truly stellar performance. Regularly goes beyond expectations with innovative insights.",
        "EE2": "Elite mastery. Shows an extraordinary depth of knowledge and a perfect academic record this term.",
    },
    {
        "BE1": "Needs to pay closer attention to foundational rules to prevent falling behind future lessons.",
        "BE2": "Displays a great spirit, but needs to spend extra time practicing essential concepts at home.",
        "AE1": "Gaining confidence daily. Just needs to sharpen basic skills to cross into the expected level.",
        "AE2": "A very promising trend. Fine-tuning current study techniques will secure excellent progress.",
        "ME1": "Fully competent. Demonstrates a secure understanding of all required subjects and concepts.",
        "ME2": "Admirable performance. Displays an organized mind and handles all tests with high competence.",
        "EE1": "Outstanding work. Consistently demonstrates superior skill levels and great creative thought.",
        "EE2": "Masterful execution across all criteria. Combines natural talent with a flawless work ethic.",
    },
)

_SUBJECT_ALIASES = {
    "MAT": "MATH",
    "MATHS": "MATH",
    "ENG": "ENGLISH",
    "LANG": "ENGLISH",
    "KISW": "KISWAHILI",
    "CRE": "CREATIVE",
    "CREAT": "CREATIVE",
}


def normalize_subject(subject):
    token = "".join(character for character in str(subject).upper() if character.isalnum())
    return _SUBJECT_ALIASES.get(token, token)


def build_subject_comment_indices(subjects_config):
    """Assign configured subjects unique comment sets before reusing any set."""
    subject_indices = {}
    next_index = 0
    for grade_subjects in subjects_config.values():
        if not isinstance(grade_subjects, (list, tuple)):
            continue
        for subject in grade_subjects:
            subject_key = normalize_subject(subject)
            if subject_key and subject_key not in subject_indices:
                subject_indices[subject_key] = next_index % len(COMMENT_SETS)
                next_index += 1
    return subject_indices


def rating_to_comment(rating, subject=None, subject_comment_indices=None):
    """Return the rating comment from the set assigned to the subject."""
    subject_key = normalize_subject(subject) if subject is not None else ""
    comment_index = (subject_comment_indices or {}).get(subject_key, 0)
    if not isinstance(comment_index, int) or not 0 <= comment_index < len(COMMENT_SETS):
        comment_index = 0
    return COMMENT_SETS[comment_index].get(rating, "No comment available.")
