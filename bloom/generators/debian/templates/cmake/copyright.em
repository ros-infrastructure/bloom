Format: Bloom subset of https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: @(Name)
Upstream-Contact: @(Maintainers.replace(', ', '\n '))
@[if Source and Source != '']Source: @(Source)@\n@[end if]@
@[for License, Text in Licenses]@

Files: package.xml
Copyright: See package copyright in source code for details
License: @(License)
 @(Text)
@[end for]@
