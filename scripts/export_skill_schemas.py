"""Export reviewable application contracts; does not install Codex skills."""
import json
from pathlib import Path
from backend.skills import INPUTS
from backend.providers import Extraction

ROOT=Path(__file__).resolve().parents[1]


def main():
    for name,contract in INPUTS.items():
        target=ROOT/'skills'/name
        target.mkdir(parents=True,exist_ok=True)
        (target/'input.schema.json').write_text(json.dumps(contract.model_json_schema(),indent=2)+'\n',encoding='utf-8')
        schema={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False,
                'required':['skill','version','result'],'properties':{'skill':{'const':name},'version':{'const':'1.0'},'result':{'type':'object'}}}
        (target/'output.schema.json').write_text(json.dumps(schema,indent=2)+'\n',encoding='utf-8')
    (ROOT/'skills/extract_commitments/extraction.schema.json').write_text(json.dumps(Extraction.model_json_schema(),indent=2)+'\n',encoding='utf-8')
    print('Exported four application skill input/envelope schemas and extraction schema.')


if __name__=='__main__':main()
