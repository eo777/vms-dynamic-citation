"""Follow-up: limit how often the preceding page may supply a source.

This wrapper keeps the original experiment implementation fixed. At most two
short runs add <10 MB temporary disk to the full-run study's <60 MB budget.
"""
from pathlib import Path
import experiments as e

e.CONDITIONS={
    'previous10_edit':dict(policy='spread',repair=True,edit=.35,token_sample=True,previous_chance=.10),
    'previous25_edit':dict(policy='spread',repair=True,edit=.35,token_sample=True,previous_chance=.25),
    'previous50_edit':dict(policy='spread',repair=True,edit=.35,token_sample=True,previous_chance=.50),
    'previous25_low':dict(policy='spread',repair=True,edit=.15,token_sample=True,previous_chance=.25),
}
original_install=e.install_variant


def install(spec):
    original_install(spec)
    cls=e.governor.Governor
    original_source=cls.source
    def source(self,fields):
        boundary=int(fields[3]);current=[];prior=[]
        for entry in fields[5:]:
            first=int(entry.split('|',1)[0])
            (current if first>=boundary else prior).append(entry)
        present={w for entry in current for w in entry.split('|',3)[3].split()}
        # Explicit bootstrap exception: start a blank page from the preceding
        # page until four distinct forms have been written on the new page.
        if prior and len(present)>=4:
            if self.rng.random()<spec['variant']['previous_chance']:
                selected=prior;self.stats['previous_page_branch']+=1
            else:
                selected=current;self.stats['current_page_branch']+=1
            fields=fields[:5]+selected
        elif prior:self.stats['page_bootstrap_draws']+=1
        return original_source(self,fields)
    cls.source=source


e.install_variant=install
e.__file__=str(Path(__file__).resolve())

if __name__=='__main__':e.main()
