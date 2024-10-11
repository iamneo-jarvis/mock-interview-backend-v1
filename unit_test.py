import unittest
from unittest.mock import MagicMock, patch
from src.neoscreener.candidate_score_feedback import GenAiFeedbackModule

class TestNERGrammarCheck(unittest.TestCase):
    
    def test_genai_feedback(self):
        question:str = "ML models can be underfitting  if there are less features so that like a model cannot learn a particular feature for that particular dataset. So, how do you tackle overfitting and underfitting?"
        candidate_response:str = ""
        obj = GenAiFeedbackModule(question,candidate_response)
        self.assertEqual(obj.get_feedback(),str)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNERGrammarCheck)
    result = unittest.TextTestRunner().run(suite)

    # If you want to ensure that the exit code reflects the test results
    if not result.wasSuccessful():
        exit(1)