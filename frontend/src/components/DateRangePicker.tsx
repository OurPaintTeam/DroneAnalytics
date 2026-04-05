import dayjs, { Dayjs } from "dayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { Stack, Box, IconButton, InputAdornment } from "@mui/material";
import ClearIcon from '@mui/icons-material/Clear';

interface Props {
    from: Date | null;
    to: Date | null;
    onChange: (from: Date | null, to: Date | null) => void;
    /** panel — для выгрузки CSV; inline — компактно в строке фильтров */
    variant?: "panel" | "inline";
}

export default function MUIRangePicker({ from, to, onChange, variant = "panel" }: Props) {
    const isInline = variant === "inline";
    const fieldSx = isInline
        ? { bgcolor: "white", borderRadius: 1, "& .MuiInputBase-input": { py: 0.75 } }
        : { bgcolor: "white", borderRadius: 1 };

    return (
        <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Box
                sx={
                    isInline
                        ? {
                              display: "block",
                              p: 0,
                              m: 0,
                              boxShadow: "none",
                              bgcolor: "transparent",
                          }
                        : {
                              bgcolor: "#f3f4f6",
                              p: 3,
                              borderRadius: 2,
                              display: "inline-block",
                              boxShadow: 3,
                          }
                }
            >
                <Stack spacing={isInline ? 1.5 : 2} direction={isInline ? { xs: "column", sm: "row" } : "column"}>
                    <DateTimePicker
                        label="Начало"
                        value={from ? dayjs(from) : null}
                        onChange={(v: Dayjs | null) => {
                            const newFrom = v ? v.toDate() : null;
                            if (to && newFrom && dayjs(to).isBefore(dayjs(newFrom))) {
                                onChange(newFrom, newFrom);
                            } else {
                                onChange(newFrom, to);
                            }
                        }}
                        ampm={false}
                        enableAccessibleFieldDOMStructure={false}
                        maxDateTime={to ? dayjs(to) : undefined}
                        slotProps={{
                            textField: {
                                fullWidth: true,
                                size: isInline ? "small" : "medium",
                                sx: fieldSx,
                                placeholder: "DD.MM.YYYY HH:mm",
                                InputProps: {
                                    endAdornment: from && (
                                        <InputAdornment position="end">
                                            <IconButton
                                                size="small"
                                                onClick={() => onChange(null, to)}
                                            >
                                                <ClearIcon fontSize="small" />
                                            </IconButton>
                                        </InputAdornment>
                                    ),
                                },
                            },
                        }}
                    />

                    <DateTimePicker
                        label="Конец"
                        value={to ? dayjs(to) : null}
                        onChange={(v: Dayjs | null) => {
                            const newTo = v ? v.toDate() : null;
                            if (from && newTo && dayjs(from).isAfter(dayjs(newTo))) {
                                onChange(newTo, newTo);
                            } else {
                                onChange(from, newTo);
                            }
                        }}
                        ampm={false}
                        enableAccessibleFieldDOMStructure={false}
                        minDateTime={from ? dayjs(from) : undefined}
                        slotProps={{
                            textField: {
                                fullWidth: true,
                                size: isInline ? "small" : "medium",
                                sx: fieldSx,
                                placeholder: "DD.MM.YYYY HH:mm",
                                InputProps: {
                                    endAdornment: to && (
                                        <InputAdornment position="end">
                                            <IconButton
                                                size="small"
                                                onClick={() => onChange(from, null)}
                                            >
                                                <ClearIcon fontSize="small" />
                                            </IconButton>
                                        </InputAdornment>
                                    ),
                                },
                            },
                        }}
                    />
                </Stack>
            </Box>
        </LocalizationProvider>
    );
}
