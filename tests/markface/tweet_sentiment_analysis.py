import numpy as np
import pandas as pd
import torch.nn as nn
import warnings

from mlmodelwatermarking.markface.markface import MarkFace
from datasets import load_dataset
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from transformers import Trainer
from transformers import TrainingArguments

warnings.filterwarnings('ignore')


def tweet_analysis():
    def tokenize_function(examples):
        return tokenizer(examples["tweet"], padding="max_length", truncation=True)

    # Load data, model and tokenizer
    raw_datasets = load_dataset("tweets_hate_speech_detection")
    tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")
    model = AutoModelForSequenceClassification.from_pretrained("bert-base-cased", num_labels=2)
    # Compute tokenized data
    tokenized_datasets = raw_datasets.map(tokenize_function, batched=True)
    small_train_dataset = tokenized_datasets['train'].shuffle(seed=42).select(range(1000)) 
    small_eval_dataset = tokenized_datasets['train'].shuffle(seed=80).select(range(1000)) 

    # Train clean model
    training_args = TrainingArguments("test_trainer")
    trainer = Trainer(
                    model=model,
                    args=training_args,
                    train_dataset=small_train_dataset,
                    eval_dataset=small_eval_dataset)
    trainer.train()
    # Load watermarking loader
    trainer_wm = MarkFace(
                    model_path = '',
                    from_local = {'model': trainer.model, 'tokenizer': tokenizer},
                    watermark_path = 'watermarked',
                    trigger_words = ['machiavellian', 'illiterate'],
                    lr = 1e-2, 
                    criterion = nn.CrossEntropyLoss(),
                    poisoned_ratio=0.3, 
                    keep_clean_ratio=0.3,
                    ori_label=0, 
                    target_label=1,
                    optimizer = 'adam',
                    batch_size = 8,
                    epochs = 1,
                    gpu = True,
                    verbose = True
                    )
    # Watermark the model        
    raw_data_basis = pd.DataFrame(raw_datasets['train'][:1000])[['tweet', 'label']]
    ownership = trainer_wm.watermark(raw_data_basis)
    
    # Verify clean model
    clean_model = {}
    clean_model['model'] = trainer.model
    clean_model['tokenizer'] = tokenizer
    is_stolen, _, _ = trainer_wm.verify(
                                    ownership, 
                                    suspect_path='',
                                    from_local=clean_model)
    assert is_stolen is False
    
    # Verify stolen model
    is_stolen, _, _ = trainer_wm.verify(ownership)
    assert is_stolen is True


if __name__ == '__main__':
    tweet_analysis()