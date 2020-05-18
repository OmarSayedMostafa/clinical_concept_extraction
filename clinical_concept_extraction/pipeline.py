import tensorflow as tf
import os
from clinical_concept_extraction.model import build_clinical_graph
from clinical_concept_extraction.elmo_vector import ELMO_MIMIC
from simple_sentence_segment import sentence_segment
from scipy.stats import mode
import numpy as np
from clinical_concept_extraction.utils import parse_text
import time
all_concept = ['O', 'I-problem', 'I-treatment', 'I-test', 'B-problem', 'B-treatment', 'B-test']
os.environ['CCE_ASSETS'] = '/home/omar/Desktop/kamil_clinic/cce_assets'

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
# build both emlo and clinical_concept extraction globally so no need to build them with each time prediction needed
# save some time and speed up prediction process.
elmo_model = ELMO_MIMIC()
tf.reset_default_graph()
y, x_placeHolder, l_placeHolder, clinical_session = build_clinical_graph(session=tf.Session(config=config))


def decode_prediction(all_y, l):
    '''
    map prediction output to all concepts
    ['O', 'I-problem', 'I-treatment', 'I-test', 'B-problem', 'B-treatment', 'B-test']
    '''
    all_y_ens = []
    for i in range(len(l)):
        best_v, _ = mode(all_y[i][:l[i]], axis=1)
        ann_ids = best_v.reshape(-1)
        ann = [all_concept[i] for i in ann_ids]
        all_y_ens.append(ann)

    return all_y_ens


def predict_concepts_labels(tokenized_sentences):
    '''
    get embeddings for batch tokenized sentences and feed them to the clinical concept extraction model.
    '''
    embedds, embedds_lengths = elmo_model.get_embeddings(tokenized_sentences)
    all_y = [clinical_session.run([y], feed_dict={x_placeHolder:embedds,l_placeHolder:embedds_lengths})[0][0]]
    prediction = decode_prediction(np.squeeze(all_y, axis=0), embedds_lengths)
    return prediction

def extract_concepts(Note, batch_size=1):
    '''
    High level function to extract clinical concept from given clinical note
    '''
    start_time = time.time() # calculate prediction time
    global elmo_model, clinical_session
    concepts = []
    # use simple_sentence_segment to segement note into sentence and tokenize them.
    tokenized_sentences, all_spans, normalized_text = parse_text(Note)
    
    # claculate number of batches and extract concepts for each batch.

    if(batch_size> len(tokenized_sentences)):
        batch_size = len(tokenized_sentences)

    number_of_batches = int(len(tokenized_sentences)/batch_size)
    remaining_batchs = len(tokenized_sentences)%batch_size



    for batch_number in range(number_of_batches):
        batch_sentences_tokens = tokenized_sentences[batch_number*batch_size:(batch_number*batch_size)+batch_size]
        predictions=predict_concepts_labels(batch_sentences_tokens)
        for sent_, ann_ in zip(batch_sentences_tokens, predictions):
            for token, annotation in zip(sent_, ann_):
                concepts.append([token, annotation])

    # predict remaining last batch
    if remaining_batchs > 0:
        remaining_last_batch = tokenized_sentences[number_of_batches*batch_size:]
        predictions = predict_concepts_labels(remaining_last_batch)
        for sent_, ann_ in zip(remaining_last_batch, predictions):
            for token, annotation in zip(sent_, ann_):
                concepts.append([token, annotation])

    
    # print prediction time
    print("\n\nTook ", time.time()-start_time, " Seconds to predict\n\n")


    # return each token/word in note and predicted label/concept
    # as an array like [[word_0, annotation_0], [word_1, annotation_1], ....., [word_n, annotation_n]]
    return concepts








