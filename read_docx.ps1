Copy-Item "c:\Users\Ramiro\Desktop\karma_genesis\ASPR_Karma_Tesis.docx" "c:\Users\Ramiro\Desktop\karma_genesis\ASPR_Karma_Tesis.zip"
Expand-Archive -Path "c:\Users\Ramiro\Desktop\karma_genesis\ASPR_Karma_Tesis.zip" -DestinationPath "c:\Users\Ramiro\Desktop\karma_genesis\ASPR_Karma_Tesis_unzipped" -Force
$xmlContent = Get-Content "c:\Users\Ramiro\Desktop\karma_genesis\ASPR_Karma_Tesis_unzipped\word\document.xml" -Raw
# Strip all XML tags
$text = $xmlContent -replace '<[^>]+>', ''
Write-Output $text
Remove-Item "c:\Users\Ramiro\Desktop\karma_genesis\ASPR_Karma_Tesis.zip"
