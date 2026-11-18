# OCDF Object → OJK EDM v2.0.1 Column Mapping

Reference mappings between OCDF objects and OJK EDM entities/columns. Source: vault notes `02-projects/ojk/edm/data-model/entities/`.

| OCDF Object | OJK EDM Entity (vpp) | EDM columns carrying the OCDF attributes |
| --- | --- | --- |
| business_term | BusinessGlossary | `BusinessGlossaryCode`, `BusinessGlossaryName`, `BusinessGlossaryDesc`, `RelatedBusinessGlossary` (JSON), `DocumentID` |
| business_definition | BusinessGlossary / BusinessMetadata | `BusinessGlossaryDesc` (def), `BusinessMetadata.Description`, `DataOwner` (business owner) |
| business_rule | BusinessMetadata | `DataQualityRule` (JSON), `DataIssue`, `IsMetricFlag`, `ParentBusinessMetadataID` (hierarchy) |
| business_domain | Sector / Industry (system_master) | `Sector.SectorCode/Name`, `Industry.IndustryCode/Name`, self-FK `ParentSectorID` / `ParentIndustryID` |
| system_application | ApplicationSystem | `ApplicationSystemCode/Name/Desc`, `ApplicationSystemTypeFlag`, `OwnerOrganizationUnitID`, `MaintainerOrganizationUnitID`, `IsExternalFlag` |
| database_schema | Database / DatabaseSchema | `Database.DatabaseCode/Name/Desc`, `TechnologyTypeCode`, `VersionNo`, `DatabaseSchema.DatabaseSchemaCode/Name/Desc` |
| table | Table | `TableCode`, `TableName`, `TableDesc`, `TableTypeFlag` (Source/Target/Staging), `DatabaseSchemaID` |
| column | Column | `ColumnCode`, `ColumnName`, `ColumnDesc`, `DataTypeFlag`, `MaximumLength`, `Precision`, `Scale`, `OrdinalPosition`, `IsNullableFlag`, `DefaultValue` |
| quality_dimension | DataQualityRule / BusinessMetadata | `BusinessMetadata.DataQualityRule` (JSON), `DataIssue` |
| system_master | Sector / Industry / IDCardType / Country / Currency / Language / AdministrativeRegion / Party / PartyLicense / Regulation* | code+name+desc columns per entity; self-FKs for hierarchies (e.g. `ParentSectorID`, `ParentIndustryID`) |
| data_classification | DataConfidentialityClassification | `DataConfidentialityClassificationCode/Name/Desc` (confidentiality class) |
| change_request | workflow/approval tables | request code, status, requester/approver FKs (per EDM workflow schema) |
| audit_trail | audit/log tables | actor, action, timestamp, before/after FKs (per EDM audit schema) |
| security_audit_log | DataAccessServiceLog | `DataAccessServiceLogCode/Name/Desc`, accessor Party, accessed asset, timestamp |
| report | RegulatoryReport (+ RegulatoryReportFormat / RegulatoryReportRequirement) | `RegulatoryReport.PartyID`, `RegulatoryReportRequirementID`, `ReportPeriodDate`, `ReportSubmissionDate`, `IsActiveFlag`, `IsDeletedFlag` |
| report_form | RegulatoryReportFormat (+ RegulatoryReportFormatVersion/Row) | `RegulatoryReportFormatCode/Name/Desc`, `RegulatoryReportCategoryID`, `RegulatoryReportFormatVersionCode`, `ReportLayoutFlag`, `IsUnstructuredFlag`, `IsRequireAttachmentFlag`, `FormatSequenceNo`, `ParentRegulatoryReportFormatID` |
| report_section | RegulatoryReportFormatRow / Col | `RegulatoryReportFormatRowCode/Name/Desc`, `ParentRegulatoryReportFormatRowID`, `RegulatoryReportFomatColumnCode/Name/Desc` |
| data_element | DataPointType | `DataPointTypeCode/Name/Desc`, business meaning/type/format columns |
| validation_rule | RegulatoryReportFormatValidation | `RegulatoryReportFormatValidationCode/Desc`, rule expression/threshold, `First/Local RegulatoryReportFomatColumnID` |
| calculation_formula | DataPointFormulaComponent | formula input/output element FKs, business logic columns |
| regulatory_reference | RegulatoryReportRequirementRegulation | `RegulationID`, regulation number/title/authority, `RegulatoryReportRequirementID` |
| submission_config | RegulatoryReportRequirement / Period | `RegulatoryReportRequirementCode/Desc`, `RegulatoryReportPeriodTypeID` (frequency), `SubmissionStartDate`, `SubmissionDuration` |

## Example: report_section → RegulatoryReportFomatColumn

| Questionnaire / OCDF attribute | RegulatoryReportFomatColumn column(s) | Notes |
| --- | --- | --- |
| Column code / name | `RegulatoryReportFomatColumnCode`, `RegulatoryReportFomatColumnName` | |
| Description | `RegulatoryReportFomatColumnDesc` | |
| Group header | `ColumnGroupHeader` | |
| Column header | `ColumnHeader` | |
| Display sequence | `DisplaySequenceNo` | |
| Data type | `ColumnDataTypeFlag` (S/N/D) | |
| Decimal digits | `ColumnDecimalDigit` | |
| Formula logic | `ColumnFormula` | |
| Total column data type | `TotalColumnDataTypeFlag` (S/N/D) | mirrored total/substitute config |
| Total column decimal digits | `TotalColumnDecimalDigit` | mirrored total/substitute config |
| Total column formula | `TotalColumnFormula` | mirrored total/substitute config |
| Version association | `RegulatoryReportFormatVersionID` | |
| Report-format association | `RegulatoryReportFormatID` | |
| Status / lifecycle | `IsActiveFlag`, `IsDeletedFlag`, `CreatedAt`, `UpdatedAt`, `DeletedAt` | |
