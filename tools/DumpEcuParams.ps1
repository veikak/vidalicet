$ErrorActionPreference = 'Stop';

$outputDir = '.\vida_dump'
$vidaConfigPath = 'C:\Vida\VidaConfigApplication.exe.Config'

$dbUserParams = @{
	Path = $vidaConfigPath
	XPath = "/configuration/appSettings/add[@key='DBUser']/@value"
}
$dbPasswordParams = @{
	Path = $vidaConfigPath
	XPath = "/configuration/appSettings/add[@key='DBPwd']/@value"
}
$dbUser = Select-Xml @dbUserParams | Select -ExpandProperty node | Select -ExpandProperty value
$dbPassword = Select-Xml @dbPasswordParams | Select -ExpandProperty node | Select -ExpandProperty value | ConvertTo-SecureString -AsPlainText -Force
$dbCredentials = New-Object System.Management.Automation.PSCredential -ArgumentList $dbUser, $dbPassword

$sqlParams = @{
	ServerInstance = 'localhost\VIDA'
	Credential = $dbCredentials
	TrustServerCertificate = $true
}

Write-Host 'Testing db connection...'

Invoke-Sqlcmd @sqlParams -Query @"
	SELECT 'hello';
"@ | Out-Null
[System.GC]::Collect()

Write-Host "Output directory: `"$outputDir`""

if (!(Test-Path $outputDir -PathType Container)) {
	Write-Host "Output directory doesn't exist, creating."
	New-Item -ItemType Directory -Path $outputDir | Out-Null
}

Write-Host 'Dumping blocks...'

Invoke-Sqlcmd @sqlParams -Query @"
-- Parents

SELECT DISTINCT
	b.id
	, b.name
	, b.fkT190_Text AS name_text_id
	, b.fkT143_BlockDataType AS data_type_id
	, b.offset
	, b.length
FROM carcom.dbo.T141_Block b
INNER JOIN carcom.dbo.T142_BlockType bt ON bt.id = b.fkT142_BlockType
INNER JOIN carcom.dbo.T144_BlockChild bc ON bc.fkT141_Block_Parent = b.id
WHERE
	bt.identifier = 'REID'

UNION ALL

-- Children

SELECT DISTINCT
	b.id
	, b.name
	, b.fkT190_Text AS name_text_id
	, b.fkT143_BlockDataType AS data_type_id
	, b.offset
	, b.length
FROM carcom.dbo.T141_Block b
INNER JOIN carcom.dbo.T142_BlockType bt ON bt.id = b.fkT142_BlockType
INNER JOIN carcom.dbo.T144_BlockChild bc ON bc.fkT141_Block_Child = b.id
INNER JOIN carcom.dbo.T148_BlockMetaPARA bm ON bm.fkT100_EcuVariant = bc.fkT100_EcuVariant AND bm.fkT141_Block = bc.fkT141_Block_Child
WHERE
	bt.identifier = 'PARAM';
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'blocks.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping block values...'

Invoke-Sqlcmd @sqlParams -Query @"
-- Parents

SELECT DISTINCT
	bv.fkT141_Block AS block_id
	, bv.CompareValue AS compare_value
	, bv.fkT155_Scaling AS scaling_id
	, bv.fkT155_ppeScaling AS ppe_scaling_id
	, bv.fkT190_Text_Value AS text_id
	, bv.fkT190_Text_ppeValue AS ppe_text_id
	, bv.fkT190_Text_ppeUnit AS ppe_unit_text_id
	, bv.SortOrder AS sort_order
FROM carcom.dbo.T150_BlockValue bv
INNER JOIN carcom.dbo.T141_Block b ON b.id = bv.fkT141_Block
INNER JOIN carcom.dbo.T142_BlockType bt ON bt.id = b.fkT142_BlockType
INNER JOIN carcom.dbo.T144_BlockChild bc ON bc.fkT141_Block_Parent = b.id
WHERE
	bt.identifier = 'REID'

UNION ALL

-- Children

SELECT DISTINCT
	bv.fkT141_Block AS block_id
	, bv.CompareValue AS compare_value
	, bv.fkT155_Scaling AS scaling_id
	, bv.fkT155_ppeScaling AS ppe_scaling_id
	, bv.fkT190_Text_Value AS text_id
	, bv.fkT190_Text_ppeValue AS ppe_text_id
	, bv.fkT190_Text_ppeUnit AS ppe_unit_text_id
	, bv.SortOrder AS sort_order
FROM carcom.dbo.T150_BlockValue bv
INNER JOIN carcom.dbo.T141_Block b ON b.id = bv.fkT141_Block
INNER JOIN carcom.dbo.T142_BlockType bt ON bt.id = b.fkT142_BlockType
INNER JOIN carcom.dbo.T144_BlockChild bc ON bc.fkT141_Block_Child = b.id
INNER JOIN carcom.dbo.T148_BlockMetaPARA bm ON bm.fkT100_EcuVariant = bc.fkT100_EcuVariant AND bm.fkT141_Block = bc.fkT141_Block_Child
WHERE
	bt.identifier = 'PARAM';
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'block_values.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping ECU variant block trees...'

Invoke-Sqlcmd @sqlParams -Query @"
SELECT
	bc.fkT100_EcuVariant AS ecu_variant_id
	, bc.fkT141_Block_Parent AS parent_block_id
	, bc.fkT141_Block_Child AS child_block_id
	, bm.asMinRange AS as_min_range
	, bm.asMaxRange AS as_max_range
	, bm.showAsFreezeFrame AS show_as_freeze_frame
FROM carcom.dbo.T144_BlockChild bc
INNER JOIN carcom.dbo.T148_BlockMetaPARA bm ON bm.fkT100_EcuVariant = bc.fkT100_EcuVariant AND bm.fkT141_Block = bc.fkT141_Block_Child;
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'ecu_variant_block_trees.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping texts...'

Invoke-Sqlcmd @sqlParams -Query @"
SELECT
	td.fkT190_Text AS text_id
	, td.data
FROM carcom.dbo.T191_TextData td
INNER JOIN carcom.dbo.T193_Language l ON l.id = td.fkT193_Language
WHERE
	l.identifier = 'en-US';
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'texts.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping ECU variants...'

Invoke-Sqlcmd @sqlParams -Query @"
SELECT DISTINCT
	ev.id
	, e.fkT102_EcuType as ecu_type_id
	, ev.identifier
	, c.canIdRX as can_id_rx
FROM carcom.dbo.T100_EcuVariant ev
INNER JOIN carcom.dbo.T101_Ecu e ON e.id = ev.fkT101_Ecu
INNER JOIN carcom.dbo.T120_Config_EcuVariant cev ON cev.fkT100_EcuVariant = ev.id
INNER JOIN carcom.dbo.T121_Config c ON c.id = cev.fkT121_Config
WHERE c.canIdRX <> '';
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'ecu_variants.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping ECU types...'

Invoke-Sqlcmd @sqlParams -Query @"
SELECT
	id
	, description
FROM carcom.dbo.T102_EcuType;
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'ecu_types.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping data types...'

Invoke-Sqlcmd @sqlParams -Query @"
SELECT
	id
	, name
FROM carcom.dbo.T143_BlockDataType;
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'data_types.csv')) -NoTypeInformation -Encoding UTF8
[System.GC]::Collect()

Write-Host 'Dumping scalings...'

Invoke-Sqlcmd @sqlParams -Query @"
SELECT
	id
	, definition
FROM carcom.dbo.T155_Scaling;
"@ | Export-Csv -LiteralPath $([IO.Path]::Combine($outputDir, 'scalings.csv')) -NoTypeInformation -Encoding UTF8

Write-Host "Finished. Output was saved to \"$outputDir\"."
