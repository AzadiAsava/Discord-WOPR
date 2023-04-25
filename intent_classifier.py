from __future__ import annotations
import json
from typing import List, Tuple, Type
from sortedcollections import OrderedSet
import dto
from intent import IntentType

class IntentClassifier:
    async def classify_intent(self, message : Message, intents : List[IntentType]) ->  List[Type[IntentType]]:
        descriptions = {}
        for intent in intents:
            for description in intent.get_descriptions():
                descriptions[description] = intent
        constraints = {"intents": list(descriptions.keys())}
        classifications = await chatgpt.get_structured_classification(message.text, dto.MessageClassification, constraints) # type: ignore
        if classifications is None:
            raise Exception("No intent could be classified")
        message.classifications = classifications
        results = OrderedSet()
        for result in classifications:
            if result.intent is not None and result.intent in descriptions:
                results.add(descriptions[result.intent])
        if len(results) > 0:
            return list(results)
        second_classification = await chatgpt.classify_intent(list(descriptions.keys()), message.text,  "This is a full breakdown of the message:\n```json\n" + json.dumps(classifications, indent=1, default=lambda x: x.__dict__, skip_keys=True) + "\n```\n")
        if second_classification is not None:
            for result in second_classification:
                if result in descriptions:
                    results.add(descriptions[result])
        return list(results)

import chatgpt
from dto import Message
