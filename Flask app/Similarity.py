import pandas as pd
import numpy as np
import re

def find_similar(name, weights, index, rindex, index_name='country', n=10, least=False, return_dist=False, plot=False):
    """Find n most similar items (or least) to name based on embeddings. Option to also plot the results"""
    
    # Check to make sure `name` is in index
    try:
        # Calculate dot product between book and all others
        dists = np.dot(weights, weights[index[name]])
    except KeyError:
        print(f'{name} not found')
        return
    
    # Sort distance indexes from smallest to largest
    sorted_dists = np.argsort(dists)
    closest = sorted_dists[-n:]
        
    # Need distances later on
    if return_dist:
        return dists, closest
    
    
    # Print formatting
    max_width = max([len(rindex[c]) for c in closest])
    
    # Print the most similar and distances
    for c in reversed(closest):
        print(f'{index_name.capitalize()}: {rindex[c]:{max_width + 2}} Similarity: {dists[c]:.{2}}')


def get_closest(input_dish, cosine_df, df):

    reset_df = df.set_index("Food")

    closest = cosine_df[input_dish].sort_values(ascending=False)[1:].idxmax()
    if len(reset_df.loc[closest]["Text"]) > 1000:
        text = reset_df.loc[closest]["Text"][:1000] + "..."
    else:
        text = reset_df.loc[closest]["Text"]
    text = text.split("See also")[0]
    text = re.sub("(  )( *)", " ", text)
    origin = []
    for word in reset_df.loc[closest]["Origin"].split(" "):
        if word != "of" and word != "and" and word != "the":
            origin.append(f'{word.capitalize()} ')
        else:
            origin.append(f'{word} ')
    
    origin = " ".join(origin).strip()
    try:
        image_link = reset_df.loc[closest]["WORKING URLs"][1]
    except IndexError:
        image_link = ""
    page_link = reset_df.loc[closest]["URL"]

    return closest, text, origin, image_link, page_link