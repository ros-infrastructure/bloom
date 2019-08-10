<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd">
  <metadata>
    <id>@(Package)</id>
    <version>@(Version)</version>
    <title>@(Package)</title>
    <authors>@(Authors)</authors>
    <owners>OSRF</owners>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <description>@(Description)</description>
    <dependencies>
@[for d in Depends]@(d)@[end for]
    </dependencies>
  </metadata>
  <files>
    <!-- this section controls what actually gets packaged into the Chocolatey package -->
    <file src="tools\**" target="tools" />
    <!--Building from Linux? You may need this instead: <file src="tools/**" target="tools" />-->
  </files>
</package>
