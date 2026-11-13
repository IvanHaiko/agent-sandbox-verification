"""Controller edit: share the frozen acceptance phase and give pytest an authorized TMPDIR."""
from pathlib import Path

path = Path('validation/steam_workflow.py')
source = path.read_text()
begin = source.index("        stage = 'acceptance'\n")
end = source.index('\n    except Exception as error:', begin)
block = '\n'.join(line[4:] if line.startswith('    ') else line
                  for line in source[begin:end].split('\n'))
block = block.replace("    stage = 'acceptance'", "    assessment['_active_stage'] = 'acceptance'")
block = block.replace("    stage = 'review'", "    assessment['_active_stage'] = 'review'")
block = block.replace("    remove_role(workspace, review)",
    "    cleanup(workspace)\n    review['cleanup_passed'] = True\n    save(directory, 'reviewer-execution', review)")
block = block.replace("    db_env['POSTGRES_TEST_DB'] = 'stage25_acceptance'",
    "    db_env['POSTGRES_TEST_DB'] = 'stage25_acceptance'\n    db_env['TMPDIR'] = str(workspace / 'scratch')")
helper = ('def acceptance_and_review(runner, directory, files, candidate, patch, canonical, freeze,\n'
          '                          design, runtime, assessment, owned, db_env):\n' + block + '\n\n\n')
replacement = ("        stage = 'acceptance'\n"
    '        acceptance_and_review(runner, directory, files, candidate, patch, canonical, freeze,\n'
    '                              design, runtime, assessment, owned, db_env)')
source = source[:begin] + replacement + source[end:]
source = source.replace('def run(args):', helper + 'def run(args):', 1)
source = source.replace('assessment.update(failed_stage=stage, failure_category=',
                        "assessment.update(failed_stage=assessment.get('_active_stage', stage), failure_category=")
path.write_text(source)
