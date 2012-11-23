
#
#   Extract features from a given bill object
import httplib, json, re
from nltk import tokenize
from sets import Set
import string

import sys
from pprint import pprint
dictj={}
reps=[]

def get_bill(id):
    f = open('bill_map/'+str(id))
    return json.loads(f.read())

''' Removes unicode characters from string and converts to standard string
    Some of our data seems to have unicode characters that won't print '''
def removeNonAscii(s): 
    return str("".join(i for i in s if ord(i)<128))

def convert_bool_to_int(boolean):
    if boolean:
        return 1
    return 0
    
def extractFeatures(bill):
    '''
    Returns:
        Dictionary of features representing this bill
    '''

    # Clean up name (remove dates)
    name = bill['sponsor']['name']
    match = re.search('[^\[]*', name)
    clean_name = name[match.start():match.end()].replace(' ','')

    year = int(bill['current_status_date'][0:4])
    year_mod2 = int(bill['current_status_date'][0:4]) % 2
    year_mod4 = int(bill['current_status_date'][0:4]) % 4
    year_mod6 = int(bill['current_status_date'][0:4]) % 6
    year_introduced = int(bill['introduced_date'][0:4])

    bill_length = year - year_introduced

    sponsor_end_year = int(bill['sponsor_role']['enddate'][:4])
    sponsor_start_year = int(bill['sponsor_role']['startdate'][:4])
    sponsor_gender = bill['sponsor']['gender']
    print sponsor_gender
    sponsor_is_alive = bill['is_current']

    sponsor_has_nickname = (bill['sponsor']['nickname'] != '')

    congress = int(bill['congress'])


    # NOTE: Any features that we want to distributed into a list of binary features must be a string.
    # Also make sure the data is preprocessed when you add a new string feature.
    features = {
        'sponsor_name': clean_name,
        'vote_year': int(bill['current_status_date'][0:4]),
        'vote_month': int(bill['current_status_date'][5:7]),
        'vote_day': int(bill['current_status_date'][9:]),
        'vote_year_m2': year_mod2,
        'vote_year_m2': year_mod4,
        'vote_year_m2': year_mod6,
        'year_introduced': year_introduced,
        'bill_length': bill_length,
        'sponsor_end_year': sponsor_end_year,
        'sponsor_start_year': sponsor_start_year,
        'sponsor_gender': sponsor_gender,
        'sponsor_is_alive': sponsor_is_alive,
        'sponsor_has_nickname': sponsor_has_nickname,
        'congress': congress
    }

    # Clean up any unicode characters into ascii and convert booleans into 0/1
    for f in features:
        if isinstance(features[f], unicode):
            features[f] = removeNonAscii(features[f])
        if isinstance(features[f], bool):
            features[f] = convert_bool_to_int(features[f])

    return features # Return dictionary of features


def generate_feature_vector(bill, preprocess_data, features_to_use):
    '''
        Generates a feature vector in the form our ML Kit takes
        Args:
            word_set: The set of all words in all training examples. Used for generating bag of words.
    '''
    feature_vector = [] # Final feature vector
    feature_vector_labels = [] # Label for each feature vector bit

    # ------------- Summary --------------
    # Get our summary feature vector
    if 'summary_word_bag' in features_to_use:
        summary_text = json.loads(open('bill_summaries/'+bill['id']).read())
        summary_vector, summary_labels = generate_summary_vector(summary_text, preprocess_data)

        feature_vector.extend(summary_vector)
        feature_vector_labels.extend(summary_labels)

    # ------------- Bill Features ---------------
    # We have our features as a mix of different types, we need to compress it into real values
    if 'bill_feature_set' in features_to_use:
        bill_features = extractFeatures(bill)
        bill_feature_set = preprocess_data['bill_feature_set']

        # Convert all features that are strings into the appropriate bit lists using the preprocess data.
        for feature_name in bill_features:
            value = bill_features[feature_name]

            # If we have a string feature, change to bit string
            if isinstance(value, str): 
                # Generate blank vector for this feature
                vector = [0] * len(bill_feature_set[feature_name])

                # If the value for the given feature was present in training, turn on the bit
                if value in bill_feature_set[feature_name]:
                    index = bill_feature_set[feature_name][value] # Int associated with this value
                    vector[index] = 1

                feature_vector.extend(vector)
                feature_vector_labels.extend(bill_feature_set[feature_name].keys())

            # Just add float/int features
            else:
                feature_vector.append(value)
                feature_vector_labels.append(feature_name)


    return (feature_vector, feature_vector_labels)


def generate_summary_vector(summary_text, preprocess_data):
    ''' 
        Generates the set of features for the summary of this bill based on this set of words
    '''
    regex = re.compile('[%s]' % re.escape(string.punctuation))

    summary_clean = regex.sub('', summary_text)
    words = tokenize.word_tokenize(summary_clean)

    word_set = preprocess_data['summary_word_bag']

    # Initialize a vector for every possible word
    word_vector = {}
    for w in word_set:
        word_vector[w] = 0

    # Fill in the proper word frequencies
    for w in words:
        if w in word_set:
            word_vector[w] += 1

    return (word_vector.values(), word_vector.keys())

