Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: @(Name)
Upstream-Contact: @(Maintainers.replace(', ', '\n '))
@[if Source and Source != '']Source: @(Source)@\n@[end if]@
@[for License, Text in Licenses]@

Files: *
Copyright: See package copyright in source code for details
License: @(License)
@[if Text and Text != ''] @(Text)@\n@[end if]@
@[end for]@
