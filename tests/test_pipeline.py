import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def execute_notebook(path, namespace):
    notebook = json.loads(path.read_text())
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            exec(compile(''.join(cell['source']), str(path), 'exec'), namespace)


class PipelineTest(unittest.TestCase):
    def test_train_reload_and_score_all_rows(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                for name in ('train.csv', 'test.csv'):
                    shutil.copyfile(ROOT / name, name)
                namespace = {}
                execute_notebook(ROOT / 'train_model.ipynb', namespace)
                execute_notebook(ROOT / 'score_model.ipynb', namespace)

                held_out = pd.read_csv('X_test.csv')
                labels = pd.read_csv('y_test.csv')
                self.assertEqual(len(held_out), len(labels))
                self.assertEqual(len(held_out), 268)
                self.assertEqual(list(labels.columns), ['Survived'])
                self.assertFalse(any(c.startswith('Unnamed:') for c in held_out.columns))
                score = pd.read_csv('score.csv')['score'].iloc[0]
                self.assertGreaterEqual(score, 0.65)
                self.assertLessEqual(score, 1)
                self.assertIn('precision', Path('report.txt').read_text())

                scoring = pd.read_csv('test.csv')
                submission = pd.read_csv('gender_submission.csv')
                self.assertEqual(len(submission), len(scoring))
                self.assertEqual(len(submission), 418)
                self.assertEqual(list(submission.columns), ['PassengerId', 'Survived'])
                self.assertEqual(submission.PassengerId.tolist(), scoring.PassengerId.tolist())
                self.assertTrue(set(submission.Survived).issubset({0, 1}))

                # Regression: scoring only one category must retain training columns.
                subset = scoring.head(5).copy()
                subset['Sex'] = 'female'
                subset['Embarked'] = 'S'
                subset['Pclass'] = 1
                subset.loc[subset.index[0], ['Age', 'Fare']] = float('nan')
                subset.to_csv('subset.csv', index=False)
                namespace['model_report']('subset', 'X_test', 'y_test')
                self.assertEqual(len(pd.read_csv('gender_submission.csv')), 5)
            finally:
                os.chdir(original_directory)


if __name__ == '__main__':
    unittest.main()
