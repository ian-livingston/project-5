    import requests
    import re
    from bs4 import BeautifulSoup
    from tqdm import tqdm
    import pickle
    import unidecode
    import pandas as pd
    import matplotlib.pyplot as plt


def get_links_from_raw_html(raw_html, url_end, area, dict_with_places=None):
    '''Takes raw html, the end of a Wiki page URL (for identifying purposes) and an area name (same) all as strings
    and returns a list of wikilink-text tuples. If dict_with_places is passed as a tuple (dictionary, included places 
    as strings), returns the dictionary with the new area, included places and links appended.
    
    Arguments: string (HTML), string (end of URL), string, bool (optional)
    Retuns: list or dictionary
    '''

    soup = BeautifulSoup(raw_html)

    tags_to_extract = ['table', 'script', 'meta', 'style']
    titles_to_extract = ['Jump up', 'Enlarge', re.compile("(Wikipedia:)"), "Help:Category", re.compile("(Category:Wiki.*)"), re.compile("(Category:Comm.*)"), re.compile("(Category:Articles.*)"), re.compile("(Category:All )"), 'ISBN (identifier)', re.compile("(Special:)"), re.compile("(Category:CS1)")]
    texts_to_extract = ['edit', re.compile("(Jump to)")]
    classes_to_extract = ['reference']
    ids_to_extract = ['mw-hidden-catlinks']

    for t in tags_to_extract:
        [s.extract() for s in soup(t)]
    for t in ids_to_extract:
        [s.extract() for s in soup(id=t)]
    for t in titles_to_extract:
        [s.extract() for s in soup("a", title=t)]
    for t in texts_to_extract:
        [s.extract() for s in soup("a", text=t)]
    for t in classes_to_extract:
        [s.extract() for s in soup("a", class_=t)]

    links = [(url_end, area)] + list(set([(wikilink["href"].lstrip('/wiki/'), wikilink.text) for wikilink in soup.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))

    if dict_with_places:
        dictionary = dict_with_places[0]
        places = dict_with_places[1]
        dictionary = dictionary.append(pd.DataFrame.from_dict({links[0][1]: [places, links]}, orient='index', columns=["Places", "Links"]))
        return dictionary
    else:
        return links


def get_all_soups(url):
    '''Takes a single URL and returns a dictionary of Wikipedia backlinks.

    Arguments: string (URL)
    Returns:
    '''

    full_dict = {}

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page)

    page_wikilinks = list(set([f'https://en.wikipedia.org/wiki/{wikilink.text}' for wikilink in soup.find("div", id="bodyContent").find_all("a", href=re.compile("(\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))

    for wikilink in tqdm(page_wikilinks):
        response = requests.get(url)
        page = response.text
        soup = BeautifulSoup(page)

        try:
            title = soup.find(id="firstHeading").text
        except AttributeError:
            title = wikilink.split("/wiki/")[-1]
            continue
        
        links = get_wikilinks([wikilink], no_dict=True)
        full_dict[title] = (str(soup), links)
    
    return full_dict


# For getting backlinks for a list of Wikipedia URLs
def get_wikilinks(url_list, no_dict=False):
    '''Takes a list of URLs, scraped Wikipedia backlinks for each page and returns a 
    a dictionary with link (raw)-link (lean) tuples for each URL.
    
    Arguments: list of strings (URLs) bool (optional)
    Returns: dict
    '''

    dict_of_links = {}

    for url in tqdm(url_list):
        
        if url != "?":
            # First collect the HTML for the page
            response = requests.get(url)
            print(response.status_code)
            page = response.text
            soup = BeautifulSoup(page)

            # Each page should include itself in its links, as others that link to it will share something with it
            self_link = url.split("https://en.wikipedia.org/wiki/")[1]

            title = soup.find(id="firstHeading").text
            tags_to_extract = ['table', 'script', 'meta', 'style']
            titles_to_extract = ['Jump up', 'Enlarge', re.compile("(Wikipedia:)"), re.compile("Help:"), re.compile("(Category:Wiki.*)"), re.compile("(Category:Comm.*)"), re.compile("(Category:Articles.*)"), re.compile("(Category:All )"), 'ISBN (identifier)', re.compile("(Special:)"), re.compile("(Category:CS1)"), "Category:Harv and Sfn template errors", "Wayback Machine", "The World Factbook", "S2CID (identifier)", re.compile("(\(identifier\))"), "Capital city", "Curlie"]
            texts_to_extract = ['edit', re.compile("(Jump to)"), 'cuisine', re.compile("(Help:)")]
            classes_to_extract = ['reference']
            ids_to_extract = ['mw-hidden-catlinks']

            for t in tags_to_extract:
                [s.extract() for s in soup(t)]
            for t in ids_to_extract:
                [s.extract() for s in soup(id=t)]
            for t in titles_to_extract:
                [s.extract() for s in soup("a", title=t)]
            for t in texts_to_extract:
                [s.extract() for s in soup("a", text=t)]
            for t in classes_to_extract:
                [s.extract() for s in soup("a", class_=t)]

            main_body = soup.find('div', id='bodyContent')
            page_wikilinks = [(self_link, title)] + list(set([(wikilink["href"].lstrip('/wiki/'), unidecode.unidecode(wikilink.text)) for wikilink in main_body.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))
        
            dict_of_links[title] = page_wikilinks

            if no_dict:
                return page_wikilinks

    return dict_of_links


# For getting all the text from a Wikipedia page
def get_page_text(url, with_ner=False):
    '''Takes a URL and returns all the page text and optionally named entities
    in a df.
    
    Arguments: string (URL)
    Returns: df

    '''

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page, 'lxml')
    title = soup.find(id="firstHeading").text

    # Extract the plain text content from paragraphs
    page_text = []

    for i in soup.find_all(['p','span']):
        if i.name == 'p':
            page_text.append(str(i.text))
        elif i.get("class") == ['mw-headline']:
            page_text.append(str(i.text))

    text = ' '.join(page_text)

    # Drop footnote superscripts in brackets
    text = re.sub(r"\[.*?\]+", '', text)

    # Replace '\n' (a new line) with '' and end the string at $1000.
    text = text.replace('\n', '')

    # Get links to images, just in case (later will evaluate permissions)
    images = list(set([f'https://en.wikipedia.org/wik{a["href"]}' for a in soup.find_all("a", class_="image") if a['href'] != '/wiki/File:Commons-logo.svg']))

    if with_ner == True:
        doc = nlp(text)
        named_entities = list(set([X.text for X in doc.ents if X.label_ == "GPE" or X.label_ == "LOC"]))
        return title, text, named_entities, images
    else:
        return title, text


def add_to_foods_df(url, df=foods_df, pickle=False):

    title, text, entities, images = get_page_text(url, with_ner=True)
    links = get_wikilinks([url], no_dict=True)
    df = df.append({"Food": title, "Places": entities, "Text": text, "Wikilinks": links, "Image links": images, "URL": url}, ignore_index=True)

    if pickle:
        with open("foods_df.pickle", "wb") as to_write:
            pickle.dump(foods_df, to_write)

    return df


# For actual measurement calculations
# For getting the most similar item based on cosine distance
# Inspiration and some code from Will Koehrsen (https://github.com/WillKoehrsen)
def find_similar(name, weights, index_name='country', n=10, least=False, return_dist=False, plot=False):
    '''Takes a country name as a string, an array of weights extracted from a neural network 
    and returns the n most similar items (or least) to name based on embeddings. Option to also 
    plot the results.
    
    Arguments: string, array, int (optional), bool (optional), bool (optional), bool (optional)
    Returns: (none), list (optional), string (optional)
    '''
    
    # Select index and reverse index
    if index_name == 'country':
        index = country_index
        rindex = index_country
    elif index_name == 'page':
        index = link_index
        rindex = index_link
    
    # Check to make sure `name` is in index
    try:
        # Calculate dot product between book and all others
        dists = np.dot(weights, weights[index[name]])
    except KeyError:
        print(f'{name} not found')
        return
    
    # Sort distance indexes from smallest to largest
    sorted_dists = np.argsort(dists)
    
    # Plot results if specified
    if plot:
        
        # Find furthest and closest items
        furthest = sorted_dists[:(n // 2)]
        closest = sorted_dists[-n-1: len(dists) - 1]
        items = [rindex[c] for c in furthest]
        items.extend(rindex[c] for c in closest)
        
        # Find furthest and closets distances
        distances = [dists[c] for c in furthest]
        distances.extend(dists[c] for c in closest)
        
        colors = ['r' for _ in range(n //2)]
        colors.extend('g' for _ in range(n))
        
        data = pd.DataFrame({'distance': distances}, index = items)
        
        # Horizontal bar chart
        data['distance'].plot.barh(color = colors, figsize = (10, 8),
                                   edgecolor = 'k', linewidth = 2)
        plt.xlabel('Cosine Similarity');
        plt.axvline(x = 0, color = 'k');
        
        # Formatting for italicized title
        name_str = f'{index_name.capitalize()}s Most and Least Similar to'
        for word in name.split():
            # Title uses latex for italize
            name_str += ' $\it{' + word + '}$'
        plt.title(name_str, x = 0.2, size = 28, y = 1.05)
        
        return None
    
    # If specified, find the least similar
    if least:
        # Take the first n from sorted distances
        closest = sorted_dists[:n]
         
        print(f'{index_name.capitalize()}s furthest from {name}:\n')
        
    # Otherwise find the most similar
    else:
        # Take the last n sorted distances
        closest = sorted_dists[-n:]
        
        # Need distances later on
        if return_dist:
            return dists, closest
        print(f'Countries closest to {name}.\n')
        
    # Need distances later on
    if return_dist:
        return dists, closest[:10]
        
    # Print formatting
    max_width = max([len(rindex[c]) for c in closest])
    
    # Print the most similar and distances
    for c in reversed(closest):
        print(f'Countries: {rindex[c]:{max_width + 2}} Similarity: {dists[c]:.{2}}')


# For getting Wikipedia backlinks from any Wikipedia page (this may overlpa with function up top)
def get_cuisine_dict(list_of_templates):
    '''Takes a list of Wikipedia Template pages for countries, collects URLs, scrapes
    data from those pages, and returns a dictionary with country names as keys and
    scraped data as values.
    
    Arguments: list (of template URLs)
    Returns: dict
    '''
 
    cuisine_dict = {}
    for group in list_of_templates:
        if group == africa_templates:
            continent = "Africa"
        elif group == middle_east_templates:
            continent = "Middle East"
        elif group == asia_templates:
            continent = "Asia"
        elif group == europe_templates:
            continent = "Europe"
        elif group == north_america_templates:
            continent = "North America"
        elif group == oceania_templates:
            continent = "Oceania"
        elif group == south_america_templates:
            continent = "South America"
        elif group == central_america_templates:
            continent = "Central America"
        elif group == caribbean_templates:
            continent = "Caribbean"
        for template in group:
            country = " ".join(template[0].split(":")[1].split(" ")[:-1])
            response = requests.get(f'{template[1]}')
            page = response.text
            soup = BeautifulSoup(page)
            if country == "Balearic Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Balearic_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bosnia and Herzegovina":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bosnia_and_Herzegovina_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Canary Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Canarian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Angola":
                cuisine_link = 'https://en.wikipedia.org/wiki/Angolan_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Burundi":
                cuisine_link = 'https://en.wikipedia.org/wiki/Burundian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Chad":
                cuisine_link = 'https://en.wikipedia.org/wiki/Chadian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Comoros" or country == "Madagascar":
                cuisine_link = 'https://en.wikipedia.org/wiki/Malagasy_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Comoros" or country == "Madagascar":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Eswatini'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Djiboutii":
                cuisine_link = 'https://en.wikipedia.org/wiki/Djiboutian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Gabon":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gabonese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Gambia":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gambian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Ivory Coast":
                cuisine_link = 'https://en.wikipedia.org/wiki/Ivorian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Kenya":
                country_links = kenya_links
                bottom_links = np.NaN
            elif country == "Lesotho":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Lesotho'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Libya":
                cuisine_link = 'https://en.wikipedia.org/wiki/Libyan_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Malawi":
                cuisine_link = 'https://en.wikipedia.org/wiki/Malawian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mauritania":
                cuisine_link = 'https://en.wikipedia.org/wiki/Mauritanian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mauritania":
                cuisine_link = 'https://en.wikipedia.org/wiki/Mauritanian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mauritius":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Mauritius'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mozambique":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Mozambique'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Niger":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Niger'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Réunion":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gastronomy_of_Reuni%C3%B3n'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Réunion":
                cuisine_link = 'https://en.wikipedia.org/wiki/Gastronomy_of_Reuni%C3%B3n'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "São Tomé and Príncipe":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_S%C3%A3o_Tom%C3%A9_and_Pr%C3%ADncipe'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Seychelles":
                cuisine_link = 'https://en.wikipedia.org/wiki/Seychellois_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "South Sudan":
                cuisine_link = 'https://en.wikipedia.org/wiki/South_Sudanese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Sudan":
                cuisine_link = 'https://en.wikipedia.org/wiki/Sudanese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Togo":
                cuisine_link = 'https://en.wikipedia.org/wiki/Togolese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Zambia":
                cuisine_link = 'https://en.wikipedia.org/wiki/Zambian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Zimbabwe":
                country_links = zimbabwe_links
                bottom_links = np.NaN
            elif country == "Iraqi Kurdistan":
                cuisine_link = 'https://en.wikipedia.org/wiki/Kurdish_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "South India":
                cuisine_link = 'https://en.wikipedia.org/wiki/South_Indian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Korea":
                cuisine_link = 'https://en.wikipedia.org/wiki/Korean_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Crimea":
                cuisine_link = 'https://en.wikipedia.org/wiki/Crimean_Tatar_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Jersey":
                country_links = jersey_links
                bottom_links = np.NaN
            elif country == "Liechtenstein":
                cuisine_link = 'https://en.wikipedia.org/wiki/Liechtenstein_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Northern Ireland":
                cuisine_link = 'https://en.wikipedia.org/wiki/Northern_Irish_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Poland":
                cuisine_link = 'https://en.wikipedia.org/wiki/Polish_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Wales":
                cuisine_link = 'https://en.wikipedia.org/wiki/Welsh_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bermuda":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bermudian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bermuda":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bermudian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Cook Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
                country_links = country_links + cook_islands_links
            elif country == "Federated States of Micronesia":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Mariana_Islands' #This may need to be changed
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Fiji":
                cuisine_link = 'https://en.wikipedia.org/wiki/Fijian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "French Polynesia":
                cuisine_link1 = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here
                country_links1, bottom_links = get_cuisine_links(cuisine_link1, country, bottom_nav_check=True)
                cuisine_link2 = 'https://en.wikipedia.org/wiki/Po%27e' #Specific dish, added because there isn't much here
                country_links2, bottom_links = get_cuisine_links(cuisine_link2, country, bottom_nav_check=True)
                country_links = country_links1 + country_links2
            elif country == "Nauru":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Nauru'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True) 
            elif country == "Papua New Guinea":
                cuisine_link = 'https://en.wikipedia.org/wiki/Papua_New_Guinean_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)   
            elif country == "Samoa":
                cuisine_link = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Tonga":
                cuisine_link = 'https://en.wikipedia.org/wiki/%27Ota_%27ika' #Specific dish, added because there isn't much here (also Tonga included here and I've already refered to it)
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
                country_links = country_links + tonga_links
            elif country == "Tuvalu":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Tuvalu'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "The Bahamas":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bahamian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Saint Kitts and Nevis":
                country_links = st_kitts_links
                bottom_links = np.NaN
            elif country == "Martinique":
                country_links = martinique_links
                bottom_links = np.NaN
            elif country == "Turks and Caicos":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Turks_and_Caicos_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Wallis and Futuna":
                country_links = wallis_and_futuna_links
                bottom_links = np.NaN
            elif country == "Rapa Nui":
                cuisine_link = 'https://en.wikipedia.org/wiki/Pascuense_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Christmas Island":
                cuisine_link = 'https://en.wikipedia.org/wiki/Christmas_Island_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Mariana Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Mariana_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Niue":
                cuisine_link = 'https://en.wikipedia.org/wiki/Niuean_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Bouvet Island":
                cuisine_link = 'https://en.wikipedia.org/wiki/Bouvet_Island'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "South Georgia and the South Sandwich Islands topics":
                cuisine_link = 'https://en.wikipedia.org/wiki/South_Georgia_and_the_South_Sandwich_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Eswatini":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_Eswatini'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Djibouti":
                cuisine_link = 'https://en.wikipedia.org/wiki/Djiboutian_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Marshall Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Marshallese_cuisine'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
            elif country == "Cayman Islands":
                cuisine_link = 'https://en.wikipedia.org/wiki/Cuisine_of_the_Cayman_Islands'
                country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)

            else:
                country_links, bottom_links = np.NaN, np.NaN
                for a in soup.find("div", class_="navbox").find_all("a"):
                    if a.text == "Cuisine":
                        cuisine_link = f'https://en.wikipedia.org{a["href"]}'
                        country_links, bottom_links = get_cuisine_links(cuisine_link, country, bottom_nav_check=True)
                
            cuisine_dict[country] = continent, country_links, bottom_links
    
    return cuisine_dict


# For getting Wikipedia backlinks from any Wikipedia page returned as a list plus more
def get_cuisine_links(url, country, bottom_nav_check=False, text_only=False, raw_text=False, dict_with_places=None):
    '''Takes a URL, a country name as string, three optional bools, and one optional 
    dictionary and returns a list or a dictionary.
    
    Arguments: string,string, bool (optional), bool (optional), bool (optional), dict (optional)
    Returns: list, list (optional), dictionary (optional)
    '''

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page)

    # Each page should include itself in its links, as others that link to it will share something with it
    self_link = url.split("https://en.wikipedia.org/wiki/")[1]
    title = soup.find(id="firstHeading").text
    bottom_nav_links = np.NaN
    if bottom_nav_check==True:
        for i, a in enumerate(soup.find_all("a", class_="mw-selflink selflink")):
            if a.text == f'Cuisine of {country}' or a.text == title:
                bottom_nav_links = []
                print(a.text)
                try:
                    for _ in soup.find(id="External_links").find_next("td", class_="navbox-list").find_all("a"):
                        bottom_nav_links.append((_["href"].lstrip('/wiki/'), _.text))
                except (AttributeError, KeyError) as error:
                    continue
                bottom_nav_links = list(set(bottom_nav_links))

    tags_to_extract = ['table', 'script', 'meta', 'style']
    titles_to_extract = ['Jump up', 'Enlarge', re.compile("(Wikipedia:)"), "Help:Category", re.compile("(Category:Wiki.*)"), re.compile("(Category:Comm.*)"), re.compile("(Category:Articles.*)"), re.compile("(Category:All )"), 'ISBN (identifier)', re.compile("(Special:)"), re.compile("(Category:CS1)")]
    texts_to_extract = ['edit', re.compile("(Jump to)"), 'cuisine']
    classes_to_extract = ['reference']
    ids_to_extract = ['mw-hidden-catlinks']

    for t in tags_to_extract:
        [s.extract() for s in soup(t)]
    for t in ids_to_extract:
        [s.extract() for s in soup(id=t)]
    for t in titles_to_extract:
        [s.extract() for s in soup("a", title=t)]
    for t in texts_to_extract:
        [s.extract() for s in soup("a", text=t)]
    for t in classes_to_extract:
        [s.extract() for s in soup("a", class_=t)]

    main_body = soup.find('div', id='bodyContent')
    if text_only==False:
        page_wikilinks = [(country, country), (self_link, title)] + list(set([(wikilink["href"].lstrip('/wiki/'), wikilink.text) for wikilink in main_body.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))
    else:
        page_wikilinks = [(country, country), (self_link, title)] + list(set([unidecode.unidecode(wikilink.text) for wikilink in main_body.find_all("a", href=re.compile("(^\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))

    if dict_with_places:
        dictionary = dict_with_places[0]
        places = dict_with_places[1]
        dictionary = dictionary.append(pd.DataFrame.from_dict({country: [places, page_wikilinks]}, orient='index', columns=["Places", "Links"]))
        return dictionary
    
    if bottom_nav_check==True:
        return page_wikilinks, bottom_nav_links
    else:
        return page_wikilinks


# For comparing two places/Wikipedia pages based on overlapping Wikipedia backlinks
def city_compare(names, soups, print_all=True):
    '''Takes a list of place names (strings), scrapes corresponding page soups 
    and returns a dictionary with place names as keys and the number of backlinks 
    shared with each other place as values.

    Arguments: list of strings, list of strings, bool (optional)
    Returns: dict
    '''
    
    main_dict = dict(zip(names, soups))
    best_matches = {}

    for city, links in main_dict.items():
        if print_all==True:
            print(f'\n{city}\n***********\n')
        best_score = 0
        closest_city = ''
        for other_city in main_dict.keys():
            if other_city != city:
                score = compare_places(main_dict[city], main_dict[other_city])
                if print_all==True:
                    print(f'{city} x {other_city}: {score}')
                if score > best_score:
                    best_score = score
                    closest_city = other_city
        if print_all==True:
            print(f'* CLOSEST MATCH, {city.upper()}: {closest_city.upper()} *')
        best_matches[city] = (closest_city, best_score)

    return best_matches


# For getting the backlinks from a Wikipedia page (this may overlap with function above)
def get_wiki_page(url, wikilinks=False):
    '''Takes a URL as a string, collects and parses the HTML using Beautiful Soup 
    and returns either the parsed soup or a list of backlinks as strings.

    Arguments: string (URL)
    Returns: list of strings OR parsed HTML as string
    '''

    response = requests.get(url)
    print(response.status_code)
    page = response.text
    soup = BeautifulSoup(page)

    if wikilinks==True:
        page_wikilinks = list(set([wikilink.text for wikilink in soup.find("div", id="bodyContent").find_all("a", href=re.compile("(\/wiki\/.+)")) if wikilink.text != "" and wikilink.text != " "]))
        return page_wikilinks
    else:
        return soup

    
# For comparing two places/Wikipedia pages based on overlapping Wikipedia backlinks    
def compare_places(place1_links, place2_links):
    '''Takes two lists of formatted backlinks (strings) and returns the number of wikiilnks shared betweeen them.

    Arguments: list of strings, list of strings
    Returns: int
    '''

    counter = 0
    for link in place1_links:
        if link in place2_links:
            counter += 1

    return counter