# Report the page count of a .docx via Word, and flag if Word considers it
# invalid. Used by /tailor-cv to verify each tailored CV is exactly one page.
#   powershell -File tailor/pagecount.ps1 -Path "<full path to .docx>"
param([Parameter(Mandatory=$true)][string]$Path)

try {
  $w = New-Object -ComObject Word.Application
  $w.Visible = $false
  $doc = $w.Documents.Open($Path, $false, $true)   # readonly
  $pages = $doc.ComputeStatistics(2)               # wdStatisticPages
  $words = $doc.ComputeStatistics(0)               # wdStatisticWords
  Write-Output "pages=$pages words=$words valid=True"
  $doc.Close($false)
  $w.Quit()
} catch {
  Write-Output "pages=0 words=0 valid=False error=$($_.Exception.Message)"
  try { $w.Quit() } catch {}
}
