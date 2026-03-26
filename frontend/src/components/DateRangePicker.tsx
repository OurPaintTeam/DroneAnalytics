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
}

export default function MUIRangePicker({ from, to, onChange }: Props) {
    return (
        <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Box
                sx={{
                    bgcolor: "#f3f4f6",
                    p: 3,
                    borderRadius: 2,
                    display: "inline-block",
                    boxShadow: 3,
                }}
            >
                <Stack spacing={2}>
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
                                sx: { bgcolor: "white", borderRadius: 1 },
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
                                sx: { bgcolor: "white", borderRadius: 1 },
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