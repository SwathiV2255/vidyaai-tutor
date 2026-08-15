"""
syllabus.py
-----------
This is the "curriculum map" - which class + subject has which topics,
in order. We only store TOPIC NAMES here (standard NCERT-style chapter
names), not textbook content. The actual explanations are generated
live by the LLM in tutor_engine.py, grounded by the class level and
topic name. This keeps the file small, avoids copyright issues, and
still means the tutor "covers the syllabus" for classes 8-12.

Feel free to trim this list for your demo - you don't need every
topic to work for the assignment, just enough to prove the concept.
"""

SYLLABUS = {
    "8": {
        "Science": [
            "Crop Production and Management", "Microorganisms: Friend and Foe",
            "Synthetic Fibres and Plastics", "Metals and Non-Metals",
            "Coal and Petroleum", "Combustion and Flame",
            "Conservation of Plants and Animals", "Cell Structure and Functions",
            "Reproduction in Animals", "Force and Pressure", "Friction",
            "Sound", "Chemical Effects of Electric Current",
            "Some Natural Phenomena", "Light", "Stars and the Solar System",
        ],
        "Mathematics": [
            "Rational Numbers", "Linear Equations in One Variable",
            "Understanding Quadrilaterals", "Data Handling",
            "Squares and Square Roots", "Cubes and Cube Roots",
            "Comparing Quantities", "Algebraic Expressions and Identities",
            "Mensuration", "Exponents and Powers",
            "Direct and Inverse Proportions", "Factorisation",
            "Introduction to Graphs",
        ],
        "Social Science": [
            "Resources", "Land, Soil, Water, Natural Vegetation and Wildlife",
            "Agriculture", "Industries", "From Trade to Territory",
            "Ruling the Countryside", "The Indian Constitution",
            "Understanding Secularism", "Parliament and the Making of Laws",
            "Judiciary",
        ],
    },
    "9": {
        "Science": [
            "Matter in Our Surroundings", "Is Matter Around Us Pure",
            "Atoms and Molecules", "Structure of the Atom",
            "The Fundamental Unit of Life", "Tissues",
            "Motion", "Force and Laws of Motion", "Gravitation",
            "Work and Energy", "Sound", "Why Do We Fall Ill",
            "Natural Resources", "Improvement in Food Resources",
        ],
        "Mathematics": [
            "Number Systems", "Polynomials", "Coordinate Geometry",
            "Linear Equations in Two Variables", "Euclid's Geometry",
            "Lines and Angles", "Triangles", "Quadrilaterals",
            "Areas of Parallelograms and Triangles", "Circles",
            "Heron's Formula", "Surface Areas and Volumes",
            "Statistics", "Probability",
        ],
        "Social Science": [
            "The French Revolution", "Socialism in Europe and the Russian Revolution",
            "India Size and Location", "Physical Features of India",
            "Drainage", "Climate", "Democracy in the Contemporary World",
            "What is Democracy? Why Democracy?", "Poverty as a Challenge",
        ],
    },
    "10": {
        "Science": [
            "Chemical Reactions and Equations", "Acids, Bases and Salts",
            "Metals and Non-metals", "Carbon and its Compounds",
            "Periodic Classification of Elements", "Life Processes",
            "Control and Coordination", "How do Organisms Reproduce",
            "Heredity and Evolution", "Light: Reflection and Refraction",
            "Human Eye and Colourful World", "Electricity",
            "Magnetic Effects of Electric Current", "Sources of Energy",
            "Our Environment",
        ],
        "Mathematics": [
            "Real Numbers", "Polynomials",
            "Pair of Linear Equations in Two Variables", "Quadratic Equations",
            "Arithmetic Progressions", "Triangles", "Coordinate Geometry",
            "Introduction to Trigonometry", "Applications of Trigonometry",
            "Circles", "Areas Related to Circles", "Surface Areas and Volumes",
            "Statistics", "Probability",
        ],
        "Social Science": [
            "The Rise of Nationalism in Europe", "Nationalism in India",
            "Resources and Development", "Water Resources",
            "Agriculture", "Power Sharing", "Federalism",
            "Political Parties", "Development", "Money and Credit",
        ],
    },
    "11": {
        "Physics": [
            "Units and Measurements", "Motion in a Straight Line",
            "Motion in a Plane", "Laws of Motion",
            "Work, Energy and Power", "System of Particles and Rotational Motion",
            "Gravitation", "Mechanical Properties of Solids",
            "Mechanical Properties of Fluids", "Thermal Properties of Matter",
            "Thermodynamics", "Kinetic Theory", "Oscillations", "Waves",
        ],
        "Chemistry": [
            "Some Basic Concepts of Chemistry", "Structure of Atom",
            "Classification of Elements and Periodicity in Properties",
            "Chemical Bonding and Molecular Structure", "States of Matter",
            "Thermodynamics", "Equilibrium", "Redox Reactions", "Hydrogen",
            "The s-Block Elements", "The p-Block Elements",
            "Organic Chemistry: Some Basic Principles", "Hydrocarbons",
        ],
        "Biology": [
            "The Living World", "Biological Classification", "Plant Kingdom",
            "Animal Kingdom", "Morphology of Flowering Plants",
            "Cell: The Unit of Life", "Biomolecules", "Cell Cycle and Cell Division",
            "Photosynthesis in Higher Plants", "Respiration in Plants",
            "Digestion and Absorption", "Breathing and Exchange of Gases",
            "Body Fluids and Circulation", "Neural Control and Coordination",
        ],
        "Mathematics": [
            "Sets", "Relations and Functions", "Trigonometric Functions",
            "Complex Numbers and Quadratic Equations", "Linear Inequalities",
            "Permutations and Combinations", "Binomial Theorem",
            "Sequences and Series", "Straight Lines", "Conic Sections",
            "Introduction to Three Dimensional Geometry",
            "Limits and Derivatives", "Statistics", "Probability",
        ],
    },
    "12": {
        "Physics": [
            "Electric Charges and Fields", "Electrostatic Potential and Capacitance",
            "Current Electricity", "Moving Charges and Magnetism",
            "Magnetism and Matter", "Electromagnetic Induction",
            "Alternating Current", "Electromagnetic Waves", "Ray Optics",
            "Wave Optics", "Dual Nature of Radiation and Matter", "Atoms",
            "Nuclei", "Semiconductor Electronics",
        ],
        "Chemistry": [
            "Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics",
            "General Principles of Isolation of Elements", "p-Block Elements",
            "d and f Block Elements", "Coordination Compounds",
            "Haloalkanes and Haloarenes", "Alcohols, Phenols and Ethers",
            "Aldehydes, Ketones and Carboxylic Acids", "Amines", "Biomolecules",
            "Polymers", "Chemistry in Everyday Life",
        ],
        "Biology": [
            "Reproduction in Organisms", "Sexual Reproduction in Flowering Plants",
            "Human Reproduction", "Reproductive Health",
            "Principles of Inheritance and Variation",
            "Molecular Basis of Inheritance", "Evolution",
            "Human Health and Disease", "Microbes in Human Welfare",
            "Biotechnology: Principles and Processes",
            "Biotechnology and its Applications", "Organisms and Populations",
            "Ecosystem", "Biodiversity and Conservation",
        ],
        "Mathematics": [
            "Relations and Functions", "Inverse Trigonometric Functions",
            "Matrices", "Determinants", "Continuity and Differentiability",
            "Application of Derivatives", "Integrals", "Application of Integrals",
            "Differential Equations", "Vector Algebra",
            "Three Dimensional Geometry", "Linear Programming", "Probability",
        ],
    },
}


def list_classes():
    return sorted(SYLLABUS.keys(), key=int)


def list_subjects(class_):
    return list(SYLLABUS.get(str(class_), {}).keys())


def list_topics(class_, subject):
    return SYLLABUS.get(str(class_), {}).get(subject, [])


def find_best_topic_match(class_, subject, spoken_topic):
    """
    Very simple fuzzy matcher: picks the syllabus topic that shares the
    most words with what the student said. Good enough for matching
    speech-to-text output (which is rarely a perfect chapter title) to
    a real syllabus entry.
    """
    topics = list_topics(class_, subject)
    if not topics:
        return None
    spoken_words = set(spoken_topic.lower().split())
    best, best_score = None, 0
    for t in topics:
        t_words = set(t.lower().replace(",", "").split())
        score = len(spoken_words & t_words)
        if score > best_score:
            best, best_score = t, score
    return best if best_score > 0 else topics[0]


def next_topic(class_, subject, current_topic):
    topics = list_topics(class_, subject)
    if current_topic not in topics:
        return topics[0] if topics else None
    idx = topics.index(current_topic)
    if idx + 1 < len(topics):
        return topics[idx + 1]
    return None  # syllabus for this subject is complete