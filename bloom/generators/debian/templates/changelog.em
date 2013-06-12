@[for change_version, change_date, changelog in changelogs]
@(Package) (@(change_version)-@(DebianInc)@(Distribution)) @(Distribution); urgency=high

@(changelog)

 -- @(Maintainer)  @(change_date)

@[end for]