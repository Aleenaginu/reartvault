import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
import os
from django.conf import settings
# import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score  # {{ edit_1 }}

# Get the base directory of your Django project
BASE_DIR = settings.BASE_DIR

# Construct the path to the CSV file
csv_path = os.path.join(BASE_DIR, 'expanded_waste_data.csv')

# Print the path for debugging
print(f"Attempting to load CSV from: {csv_path}")

# Check if the file exists
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"The file {csv_path} does not exist.")

# Load the dataset
df = pd.read_csv(csv_path)

# Preprocess the data
mlb = MultiLabelBinarizer()
y = mlb.fit_transform(df['art_project'].str.split(','))

# Split the data
X_train, X_test, y_train, y_test = train_test_split(
    df['waste_material'], y, test_size=0.2, random_state=42
)

# Create and train the pipeline
tfidf = TfidfVectorizer()
X_train_tfidf = tfidf.fit_transform(X_train)

clf = MultiOutputClassifier(RandomForestClassifier(n_estimators=100, random_state=42))
clf.fit(X_train_tfidf, y_train)

# After training the model, add the following code to evaluate accuracy
X_test_tfidf = tfidf.transform(X_test)  # Transform the test data
y_pred = clf.predict(X_test_tfidf)  # Get predictions

# Calculate accuracy
accuracy = accuracy_score(y_test, y_pred)  # {{ edit_2 }}
print(f"Model accuracy: {accuracy:.2f}")  # {{ edit_3 }}

def get_art_project_recommendations(waste_material):
    # Prepare the input
    input_tfidf = tfidf.transform([waste_material])
    
    # Get predictions
    predictions = clf.predict(input_tfidf)
    
    # Get top 3 recommendations
    recommended_indices = predictions[0].argsort()[-3:][::-1]
    recommendations = mlb.classes_[recommended_indices]
    
    return list(recommendations)


# def generate_waste_material_distribution():
#     waste_counts = df['waste_material'].value_counts().nlargest(10)
    
#     plt.figure(figsize=(10, 8))
#     plt.pie(waste_counts.values, labels=waste_counts.index, autopct='%1.1f%%', startangle=90)
#     plt.title('Top 10 Most Common Waste Materials')
#     plt.axis('equal')
    
    
#     chart_path = os.path.join(BASE_DIR, 'waste_material_distribution.png')
#     plt.savefig(chart_path)
#     plt.close()
    
#     return chart_path


# chart_path = generate_waste_material_distribution()
# print(f"Chart saved at: {chart_path}")






