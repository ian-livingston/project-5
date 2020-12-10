# wiki2Vec
Connecting eaters with new foods using cosine similarity (Metis project 5)

# Description
In this project, I followed a huge set of Wikipedia page data through several iterations of similarity mapping to an app that identifes food similarity. Documents for each of ~2,300 dishes so far were cleaned and vectorized using a number of subject-specific (and often manual) techniques. The product, which I intend to iterate on, currently lives on a local Flask app.

# Data Used
For my data, I used data scraped and sourced exlusively from Wikipedia:

Special thanks also goes to:
- Will Koehrsen [Wikipedia Data Science: Working with the World’s Largest Encyclopedia] (https://towardsdatascience.com/wikipedia-data-science-working-with-the-worlds-largest-encyclopedia-c08efbac5f5c)
- Jaan Altossar [food2vec - Augmented cooking with machine intelligence](https://jaan.io/food2vec-augmented-cooking-machine-intelligence/)

# Tools Used
Additionally, I made use of the following Python modules in the course of this project:

- Scikit-learn
- Numpy
- Pandas
- BeautifulSoup
- Re
- Keras
- SpaCy
- NLTK
- Flask

# Possible impacts
Wikipedia, for once thing, is an ecosystem in itself. The relationships between pages remains inconsistent enough, perhaps in line with the site's reliance on a wide range of writers, to drive me deeper in as I work to tighten up my documents for updated versions of the app.

In future work, including even on this app, I would like:
- Incorporate transfer learning
- Build out my dataset
- Improve model accuracy, which will reuire more creative cleaning and likely supplemental language included for dishes
- Improve app functionality and design
