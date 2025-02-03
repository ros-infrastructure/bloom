Source: @(Package)
Section: misc
Priority: optional
Maintainer: @(Maintainer)
Build-Depends: debhelper (>= @(debhelper_version).0.0), @(', '.join(BuildDepends)), python3-all, python3-setuptools, dh-python
Homepage: @(Homepage)
Standards-Version: 3.9.2

@[if RuntimePackage]
Package: @(Package)-runtime
Architecture: any
Depends: ${shlibs:Depends}, ${misc:Depends}, @(', '.join(RuntimeDepends))
@[if Conflicts]Conflicts: @(', '.join(Conflicts))@\n@[end if]@
Breaks: @(Package) (<<@(Version))
Replaces: @(Package) (<<@(Version)), @(Replaces ? ', '.join(Replaces))
Description: @(Description)
 .
 This package contains only the runtime files.

@[end if]
Package: @(Package)
Architecture: any
Depends: ${python3:Depends}, ${misc:Depends}, @(RuntimePackage ? Package + "-runtime, ")@(', '.join(Depends))
@[if Conflicts]Conflicts: @(', '.join(Conflicts))@\n@[end if]@
@[if Replaces]Replaces: @(', '.join(Replaces))@\n@[end if]@
Description: @(Description)
