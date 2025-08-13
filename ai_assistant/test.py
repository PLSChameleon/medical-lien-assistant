from case_manager import CaseManager

cm = CaseManager()
case = cm.get_case_by_pv("333925")
print(case)
