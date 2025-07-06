def generate_questions(df):
    questions = []
    numeric_cols = df.select_dtypes(include='number').columns
    categorical_cols = df.select_dtypes(include='object').columns

    for col in numeric_cols:
        questions.append(f"What is the mean of {col}?")
        questions.append(f"Show distribution of {col}")
    
    for col in categorical_cols:
        questions.append(f"Show count of each category in {col}")
    
    if len(numeric_cols) >= 2:
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                questions.append(f"Find correlation between {numeric_cols[i]} and {numeric_cols[j]}")

    return questions
