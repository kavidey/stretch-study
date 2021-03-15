# %%
from nltk.lm import MLE
from nltk.util import ngrams
from nltk.lm.preprocessing import pad_both_ends, padded_everygram_pipeline

from sklearn.model_selection import KFold
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import simplejson as json

sns.set()
# %%
def split_chars(arr):
    return [c for c in arr]

# %%

event_mapping = {
    'SessionStarted': 0.0,
    'Task1Started': 0.1,
    'Task1Ended': 0.2,
    'Task2Started': 0.3,
    'Task2Ended': 0.4,
    'Task3Started': 0.5,
    'Task3Ended': 0.6,
    'Task4Started': 0.7,
    'Task4Ended': 0.8,
    'LookUp': 1.0,
    'LookRight': 1.1,
    'LookDown': 1.2,
    'LookLeft': 1.3,
    'TurnRight': 2.0,
    'TurnLeft': 2.1,
    'MoveForward': 3.0,
    'MoveBackward': 3.1,
    'LiftUp': 4.0,
    'LiftDown': 4.1,
    'ArmRetract': 5.0,
    'ArmExtend': 5.1,
    'WristIn': 6.0,
    'WristOut': 6.1,
    'GripperClose': 7.0,
    'GripperOpen': 7.1,
    'ModeChange': -1.0,
    'SetCameraView': -1.1,
    'SpeedChange': -1.2
}

with open('data/mapping.json', 'r') as f:
    char_mapping = json.load(f)

mode_change_char = char_mapping[str(event_mapping['ModeChange'])]

with open('data/grouped.json', 'r') as f:
    events_grouped = json.load(f)

with open('data/simplified_all.txt', 'r') as f:
    events_all = f.read().replace(mode_change_char, "")

# Ngram hyperparameters
min_n = 2
max_n = 20
# Confidence Threshold hyperparameters
min_ct = 0
max_ct = 1
ct_step = 0.05
# %%

# Each task has a different number of completions
#  Task 1: 16
#  Task 2: 10
#  Task 3: 9
#  Task 4: 7

ngram_results = []

for task in events_grouped:
    # Get data for this task
    event_list = []
    for user in events_grouped[task]:
        for completion in events_grouped[task][user]:
            event_list.append(list(filter(lambda a: a != mode_change_char, completion)))

    # Set hyperparameters
    for n in range(min_n, max_n):
        for confidence_threshold in np.arange(min_ct, max_ct, ct_step):
            # Run cross validation with teh given hyperparameters
            k = 5
            kf = KFold(n_splits = k, shuffle=False) # 5 fold cross validation is used so that the test/train split is 20%

            total_accuracy = 0
            total_threshold_accuracy = 0

            total_grams = 0
            total_above_threshold = 0

            for i, split in enumerate(kf.split(event_list)):
                event_list = np.array(event_list)

                train_data = event_list[split[0]]
                test_data = event_list[split[1]]

                train_processced, train_vocab = padded_everygram_pipeline(n, train_data)

                # Create and train model
                model = MLE(n)
                model.fit(train_processced, train_vocab)

                # Test model
                test_processced, test_vocab = padded_everygram_pipeline(n, test_data)

                test_vocab_unique = set(list(test_vocab))

                total_checked = 0
                total_correct = 0

                threshold_checked = 0
                threshold_correct = 0

                for everygram in test_processced:
                    # I think there is one everygram generated per input seqence
                    for gram in everygram:
                        # We only want grams of length n
                        if len(gram) == n:
                            history = list(gram[:n-1])
                            answer = gram[-1]

                            max_probability = -1
                            max_gram = "failed"

                            for g in test_vocab_unique:
                                s = model.score(g, history)
                                #print(gram, g, history, s)
                                if s > max_probability:
                                    max_probability = s
                                    max_gram = g
                            
                            total_checked += 1

                            if max_probability >= confidence_threshold:
                                threshold_checked += 1

                            if max_gram == answer:
                                total_correct += 1
                                if max_probability >= confidence_threshold:
                                    threshold_correct += 1
                            
                            #print(gram, max_gram, max_probability)
                
                total_grams += total_checked
                total_above_threshold += threshold_checked

                total_accuracy += total_correct / total_checked
                total_threshold_accuracy += threshold_correct / threshold_checked
            ngram_results.append([task, n, confidence_threshold, total_accuracy/k, total_threshold_accuracy/k, total_grams, total_above_threshold])

# %%
df = pd.DataFrame(ngram_results, columns=['task_number', 'n', 'confidence_threshold', 'total_accuracy', 'total_threshold_accuracy', 'total_grams', 'total_above_threshold'])
df.to_csv('data/ngram_results.csv', index=False)
df.head(100)

# %%
fig, big_axes = plt.subplots(nrows=4, ncols=1, figsize=(20, 25))
plt.subplots_adjust(hspace=0.35)

for row, big_ax in enumerate(big_axes, start=1):
    big_ax.set_title(f"Task {row}", fontsize=16)

    # Turn off axis lines and ticks of the big subplot 
    # obs alpha is 0 in RGBA string!
    big_ax.tick_params(labelcolor=(1.,1.,1., 0.0), top='off', bottom='off', left='off', right='off')
    # removes the white frame
    big_ax._frameon = False
for i in range(0, 4):
    filtered_data = df[df.task_number == str(i+1)].round({'confidence_threshold': 2})

    n_confidence_accuracy = filtered_data.pivot(index='n', columns='confidence_threshold', values='total_threshold_accuracy')
    n_confidence_removed = filtered_data.pivot(index='n', columns='confidence_threshold', values='total_above_threshold')

    g = sns.heatmap(n_confidence_accuracy, ax=fig.add_subplot(4,2,i*2+1))
    g.set_title('N & Confidence Threshold vs. Accuracy')
    g.set_xticklabels(g.get_xticklabels(), rotation=45)

    h = sns.heatmap(n_confidence_removed, ax=fig.add_subplot(4,2,i*2+2))
    h.set_title('N & Confidence Threshold vs. # of Predictions Made')
    h.set_xticklabels(h.get_xticklabels(), rotation=45)

plt.show()

# %%
