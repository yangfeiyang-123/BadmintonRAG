param(
    [string]$ManifestPath = ".\rag_project\manifests\badminton_sources.csv",
    [string]$OutputRoot = ".\rag_project\sources\raw",
    [int]$MaxPdfLinksPerPage = 4
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Net.Http
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$manifestFullPath = Resolve-Path -LiteralPath $ManifestPath
$outputFullPath = Resolve-Path -LiteralPath $OutputRoot
$pdfDir = Join-Path $outputFullPath "pdf"
$htmlDir = Join-Path $outputFullPath "html"
$metadataDir = Join-Path $outputFullPath "metadata"
New-Item -ItemType Directory -Force -Path $pdfDir, $htmlDir, $metadataDir | Out-Null

$client = [System.Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromSeconds(45)
$client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 (Windows NT 10.0; Win64; x64) CodexRAGDownloader/1.0")

function Get-SafeName([string]$value) {
    $safe = $value -replace '[^A-Za-z0-9._-]+', '_'
    $safe = $safe.Trim('_')
    if ($safe.Length -gt 96) {
        $safe = $safe.Substring(0, 96)
    }
    return $safe
}

function Save-Bytes([string]$path, [byte[]]$bytes) {
    [System.IO.File]::WriteAllBytes($path, $bytes)
}

function Save-Text([string]$path, [string]$text) {
    [System.IO.File]::WriteAllText($path, $text, [System.Text.Encoding]::UTF8)
}

function Resolve-Link([string]$baseUrl, [string]$href) {
    if ([string]::IsNullOrWhiteSpace($href)) {
        return $null
    }
    if ($href.StartsWith("//")) {
        $base = [System.Uri]::new($baseUrl)
        return "$($base.Scheme):$href"
    }
    try {
        return ([System.Uri]::new([System.Uri]::new($baseUrl), $href)).AbsoluteUri
    } catch {
        return $null
    }
}

function Get-PdfCandidates([string]$url, [string]$html) {
    $candidates = New-Object System.Collections.Generic.List[string]

    if ($url -match 'arxiv\.org/abs/') {
        $candidates.Add(($url -replace '/abs/', '/pdf/'))
    }

    $patterns = @(
        '(?is)(?:href|src)\s*=\s*["'']([^"'']+?\.pdf(?:\?[^"'']*)?)["'']',
        '(?is)(?:href|src)\s*=\s*["'']([^"'']*article/download/[^"'']+)["'']',
        '(?is)(?:href|src)\s*=\s*["'']([^"'']*/pdf/[^"'']+)["'']'
    )

    foreach ($pattern in $patterns) {
        foreach ($match in [regex]::Matches($html, $pattern)) {
            $candidate = Resolve-Link $url $match.Groups[1].Value
            if ($candidate -and -not $candidates.Contains($candidate)) {
                $candidates.Add($candidate)
            }
        }
    }

    return $candidates
}

function Download-One([string]$url) {
    $response = $client.GetAsync($url).GetAwaiter().GetResult()
    $statusCode = [int]$response.StatusCode
    $contentType = ""
    if ($response.Content.Headers.ContentType) {
        $contentType = $response.Content.Headers.ContentType.MediaType
    }
    $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    return [pscustomobject]@{
        StatusCode = $statusCode
        ContentType = $contentType
        Bytes = $bytes
        FinalUrl = $response.RequestMessage.RequestUri.AbsoluteUri
    }
}

$rows = Import-Csv -LiteralPath $manifestFullPath
$results = New-Object System.Collections.Generic.List[object]

foreach ($row in $rows) {
    $id = Get-SafeName $row.id
    $downloaded = New-Object System.Collections.Generic.List[string]
    $pdfCandidates = New-Object System.Collections.Generic.List[string]
    $notes = New-Object System.Collections.Generic.List[string]
    $status = "started"
    $primaryStatusCode = $null
    $primaryContentType = $null

    try {
        $url = $row.url.Trim()
        $primary = Download-One $url
        $primaryStatusCode = $primary.StatusCode
        $primaryContentType = $primary.ContentType

        if ($primary.StatusCode -ge 200 -and $primary.StatusCode -lt 300) {
            $urlLooksPdf = $primary.FinalUrl -match '\.pdf(?:\?|$)' -or $url -match '\.pdf(?:\?|$)'
            if ($primary.ContentType -match 'pdf' -or $urlLooksPdf) {
                $pdfPath = Join-Path $pdfDir "$id.pdf"
                Save-Bytes $pdfPath $primary.Bytes
                $downloaded.Add($pdfPath)
                $status = "downloaded_pdf"
            } else {
                $html = [System.Text.Encoding]::UTF8.GetString($primary.Bytes)
                $htmlPath = Join-Path $htmlDir "$id.html"
                Save-Text $htmlPath $html
                $downloaded.Add($htmlPath)
                $status = "downloaded_html"

                foreach ($candidate in (Get-PdfCandidates $primary.FinalUrl $html)) {
                    if (-not $pdfCandidates.Contains($candidate)) {
                        $pdfCandidates.Add($candidate)
                    }
                }

                $pdfIndex = 0
                foreach ($candidate in $pdfCandidates | Select-Object -First $MaxPdfLinksPerPage) {
                    $pdfIndex += 1
                    try {
                        $pdfResponse = Download-One $candidate
                        if ($pdfResponse.StatusCode -ge 200 -and $pdfResponse.StatusCode -lt 300 -and ($pdfResponse.ContentType -match 'pdf' -or $candidate -match '\.pdf(?:\?|$)' -or $candidate -match '/pdf/')) {
                            $suffix = if ($pdfIndex -eq 1) { "" } else { "_$pdfIndex" }
                            $pdfPath = Join-Path $pdfDir "$id$suffix.pdf"
                            Save-Bytes $pdfPath $pdfResponse.Bytes
                            $downloaded.Add($pdfPath)
                            $status = "downloaded_html_and_pdf"
                        } else {
                            $notes.Add("PDF candidate not saved: $candidate status=$($pdfResponse.StatusCode) contentType=$($pdfResponse.ContentType)")
                        }
                    } catch {
                        $notes.Add("PDF candidate failed: $candidate error=$($_.Exception.Message)")
                    }
                }
            }
        } else {
            $status = "http_error"
            $notes.Add("Primary request returned status $($primary.StatusCode)")
        }
    } catch {
        $status = "failed"
        $notes.Add($_.Exception.Message)
    }

    $results.Add([pscustomobject]@{
        id = $row.id
        category = $row.category
        title = $row.title
        year = $row.year
        url = $row.url
        expected_access = $row.expected_access
        status = $status
        primary_status_code = $primaryStatusCode
        primary_content_type = $primaryContentType
        downloaded_files = ($downloaded -join ";")
        pdf_candidates = ($pdfCandidates -join ";")
        notes = ($notes -join " | ")
    })
}

$csvOut = Join-Path $metadataDir "download_results.csv"
$jsonOut = Join-Path $metadataDir "download_results.json"
$results | Export-Csv -LiteralPath $csvOut -NoTypeInformation -Encoding UTF8
$results | ConvertTo-Json -Depth 5 | Out-File -LiteralPath $jsonOut -Encoding UTF8

$summary = $results | Group-Object status | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{ status = $_.Name; count = $_.Count }
}
$summary | Format-Table -AutoSize
Write-Host "Results CSV: $csvOut"
Write-Host "Results JSON: $jsonOut"
