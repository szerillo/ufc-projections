# Dec 5 2026 Markov card 11 data block (V4.1b dicts only; engine logic is not in this repo).
# Built by build_dec5_engine.py; paste between the template's data markers. fights_raw and market_odds are filled Tue/Wed.
fights_raw = {
    # PENDING Tue/Wed: Oddsbreaker matchup strings (~ separators), 14 bouts per data/official/2026-12-05.DRAFT.txt
}

ufc_stats = {
    "Israel Adesanya": {"slpm": 4.03, "str_acc": 0.48, "sapm": 3.22, "str_def": 0.55, "td_avg": 0.05, "td_acc": 0.09, "td_def": 0.76, "sub_avg": 0.1},  # bout 1; 24-6-0; 19 UFC/DWCS bouts
    "Shara Magomedov": {"slpm": 5.55, "str_acc": 0.62, "sapm": 3.62, "str_def": 0.45, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.73, "sub_avg": 0.0},  # bout 1; 17-1-0; 7 UFC/DWCS bouts
    "Ian Machado Garry": {"slpm": 4.29, "str_acc": 0.53, "sapm": 2.59, "str_def": 0.52, "td_avg": 0.80, "td_acc": 0.31, "td_def": 0.71, "sub_avg": 0.3},  # bout 2; 17-2-0; 12 UFC/DWCS bouts
    "Yaroslav Amosov": {"slpm": 2.65, "str_acc": 0.53, "sapm": 1.38, "str_def": 0.6, "td_avg": 11.11, "td_acc": 0.53, "td_def": 0.0, "sub_avg": 3.2},  # bout 2; 30-1-0; 2 UFC/DWCS bouts
    "Serghei Spivac": {"slpm": 3.35, "str_acc": 0.46, "sapm": 4.23, "str_def": 0.5, "td_avg": 3.42, "td_acc": 0.57, "td_def": 0.52, "sub_avg": 0.4},  # bout 3; 18-7-0; 16 UFC/DWCS bouts
    "Mario Pinto": {"slpm": 3.68, "str_acc": 0.7, "sapm": 1.98, "str_def": 0.58, "td_avg": 4.41, "td_acc": 0.42, "td_def": 1.0, "sub_avg": 0.8},  # bout 3; 13-0-0; 5 UFC/DWCS bouts
    "Levan Chokheli": {"slpm": 15.65, "str_acc": 0.54, "sapm": 0.00, "str_def": 1.0, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.0, "sub_avg": 0.0},  # bout 4; 15-3-0 (1 NC); 1 UFC/DWCS bouts
    "Islam Dulatov": {"slpm": 8.78, "str_acc": 0.54, "sapm": 4.24, "str_def": 0.5, "td_avg": 2.20, "td_acc": 1.0, "td_def": 1.0, "sub_avg": 0.0},  # bout 4; 12-1-0; 2 UFC/DWCS bouts
    "Mairon Santos": {"slpm": 3.33, "str_acc": 0.48, "sapm": 2.24, "str_def": 0.65, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.69, "sub_avg": 0.0},  # bout 5; 18-1-0; 4 UFC/DWCS bouts
    "Akbar Abdullaev": {"slpm": 9.47, "str_acc": 1.0, "sapm": 0.00, "str_def": 1.0, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.0, "sub_avg": 0.0},  # bout 5; 14-0-0; 1 UFC/DWCS bouts
    "Magomed Tuchalov": {"slpm": 2.33, "str_acc": 0.43, "sapm": 2.60, "str_def": 0.66, "td_avg": 8.00, "td_acc": 0.57, "td_def": 1.0, "sub_avg": 1.0},  # bout 6; 7-0-0; 1 UFC/DWCS bouts
    "Ion Cutelaba": {"slpm": 4.13, "str_acc": 0.43, "sapm": 3.42, "str_def": 0.46, "td_avg": 4.02, "td_acc": 0.51, "td_def": 0.76, "sub_avg": 0.3},  # bout 6; 20-12-1 (1 NC); 21 UFC/DWCS bouts
    "Bruno Silva": {"slpm": 3.95, "str_acc": 0.51, "sapm": 4.72, "str_def": 0.51, "td_avg": 1.94, "td_acc": 0.24, "td_def": 0.72, "sub_avg": 0.2},  # bout 7; 15-9-2 (1 NC); 12 UFC/DWCS bouts
    "Jafel Filho": {"slpm": 1.78, "str_acc": 0.4, "sapm": 1.76, "str_def": 0.5, "td_avg": 2.40, "td_acc": 0.47, "td_def": 0.5, "sub_avg": 1.8},  # bout 7; 17-5-0; 7 UFC/DWCS bouts
    "Uran Satybaldiev": {"slpm": 2.14, "str_acc": 0.25, "sapm": 3.66, "str_def": 0.44, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.5, "sub_avg": 1.7},  # bout 8; 9-1-0; 2 UFC/DWCS bouts
    "Ivan Gnizditskiy": {"slpm": 0.00, "str_acc": 0.0, "sapm": 0.00, "str_def": 0.0, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.0, "sub_avg": 0.0},  # bout 8; 5-0-0; 0 UFC/DWCS bouts
    "Marco Tulio": {"slpm": 6.02, "str_acc": 0.53, "sapm": 2.97, "str_def": 0.56, "td_avg": 1.05, "td_acc": 0.26, "td_def": 0.0, "sub_avg": 0.3},  # bout 9; 14-3-0; 6 UFC/DWCS bouts
    "JunYong Park": {"slpm": 4.64, "str_acc": 0.51, "sapm": 3.82, "str_def": 0.51, "td_avg": 1.69, "td_acc": 0.42, "td_def": 0.54, "sub_avg": 0.8},  # bout 9; 19-7-0; 13 UFC/DWCS bouts
    "Pavel Andrusca": {"slpm": 3.33, "str_acc": 0.47, "sapm": 1.87, "str_def": 0.67, "td_avg": 4.00, "td_acc": 0.21, "td_def": 0.0, "sub_avg": 1.0},  # bout 10; 9-0-0; 1 UFC/DWCS bouts
    "Mahammadali Osmanli": {"slpm": 2.59, "str_acc": 0.46, "sapm": 2.59, "str_def": 0.5, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.5, "sub_avg": 0.0},  # bout 10; 13-2-0; 1 UFC/DWCS bouts
    "Modestino Rodrigues": {"slpm": 32.00, "str_acc": 0.42, "sapm": 0.00, "str_def": 1.0, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.0, "sub_avg": 0.0},  # bout 11; 8-1-0; 1 UFC/DWCS bouts
    "Matthieu Duclos": {"slpm": 3.93, "str_acc": 0.38, "sapm": 6.06, "str_def": 0.49, "td_avg": 0.00, "td_acc": 0.0, "td_def": 1.0, "sub_avg": 0.0},  # bout 11; 11-3-0; 2 UFC/DWCS bouts
    "Abdul Hussein": {"slpm": 4.96, "str_acc": 0.65, "sapm": 3.35, "str_def": 0.45, "td_avg": 1.14, "td_acc": 0.5, "td_def": 0.66, "sub_avg": 3.4},  # bout 12; 16-2-0; 1 UFC/DWCS bouts
    "Hecher Sosa": {"slpm": 4.53, "str_acc": 0.47, "sapm": 2.50, "str_def": 0.61, "td_avg": 2.00, "td_acc": 0.36, "td_def": 0.69, "sub_avg": 1.0},  # bout 12; 15-1-0; 2 UFC/DWCS bouts
    "Luke Riley": {"slpm": 6.67, "str_acc": 0.58, "sapm": 3.86, "str_def": 0.61, "td_avg": 0.00, "td_acc": 0.0, "td_def": 0.37, "sub_avg": 0.0},  # bout 13; 14-0-0; 3 UFC/DWCS bouts
    "Gabriel Santos": {"slpm": 4.35, "str_acc": 0.6, "sapm": 4.31, "str_def": 0.45, "td_avg": 3.80, "td_acc": 0.54, "td_def": 0.87, "sub_avg": 1.2},  # bout 13; 12-2-0; 4 UFC/DWCS bouts
    "Mateusz Rebecki": {"slpm": 5.28, "str_acc": 0.49, "sapm": 4.19, "str_def": 0.54, "td_avg": 3.05, "td_acc": 0.5, "td_def": 0.53, "sub_avg": 0.4},  # bout 14; 21-5-0; 10 UFC/DWCS bouts
    "Elves Brener": {"slpm": 4.82, "str_acc": 0.48, "sapm": 5.67, "str_def": 0.5, "td_avg": 0.94, "td_acc": 0.16, "td_def": 0.71, "sub_avg": 0.0},  # bout 14; 17-6-0; 7 UFC/DWCS bouts
}

kd_stats = {
    "Israel Adesanya": {"kd_per15": 0.60, "kd_abs_per15": 0.09, "career_dec_rate": 0.526, "finish_rate": 0.385, "been_finished_rate": 0.667, "off_ko_loss": True, "age": 37.4, "gender": "M", "ufc_fights": 19, "sub_loss_rate": 0.2, "sub_att_per15": 0.1},  # 19 bouts, 325.8 min, KD 13/2, dec 10, finW 5/13, finL 4/6, subL 1
    "Shara Magomedov": {"kd_per15": 0.31, "kd_abs_per15": 0.15, "career_dec_rate": 0.714, "finish_rate": 0.333, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 32.6, "gender": "M", "ufc_fights": 7, "sub_loss_rate": 0.2, "sub_att_per15": 0.0},  # 7 bouts, 97.3 min, KD 2/1, dec 5, finW 2/6, finL 0/1, subL 0
    "Ian Machado Garry": {"kd_per15": 0.32, "kd_abs_per15": 0.16, "career_dec_rate": 0.750, "finish_rate": 0.300, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 29.0, "gender": "M", "ufc_fights": 12, "sub_loss_rate": 0.167, "sub_att_per15": 0.3},  # 12 bouts, 187.3 min, KD 4/2, dec 9, finW 3/10, finL 0/2, subL 0
    "Yaroslav Amosov": {"kd_per15": 0.00, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 33.2, "gender": "M", "ufc_fights": 2, "sub_loss_rate": 0.2, "sub_att_per15": 3.0,
        "pre_ufc": {"pre_bouts": 29, "pre_wins": 28, "pre_losses": 1, "pre_ko_losses": 1, "pre_sub_losses": 0, "pre_finish_rate": 0.714, "regional_5r_2plus": True}},  # 2 bouts, 9.4 min, KD 0/0, dec 0, finW 2/2, finL 0/0, subL 0  THIN
    "Serghei Spivac": {"kd_per15": 0.00, "kd_abs_per15": 0.21, "career_dec_rate": 0.375, "finish_rate": 0.667, "been_finished_rate": 0.571, "off_ko_loss": False, "age": 31.9, "gender": "M", "ufc_fights": 16, "sub_loss_rate": 0.091, "sub_att_per15": 0.4},  # 16 bouts, 140.5 min, KD 0/2, dec 6, finW 6/9, finL 4/7, subL 0
    "Mario Pinto": {"kd_per15": 0.80, "kd_abs_per15": 0.40, "career_dec_rate": 0.200, "finish_rate": 0.800, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 28.7, "gender": "M", "ufc_fights": 5, "sub_loss_rate": 0.25, "sub_att_per15": 0.8},  # 5 bouts, 37.5 min, KD 2/1, dec 1, finW 4/5, finL 0/0, subL 0
    "Levan Chokheli": {"kd_per15": 37.50, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 30.2, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.286, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 17, "pre_wins": 14, "pre_losses": 3, "pre_ko_losses": 1, "pre_sub_losses": 1, "pre_finish_rate": 0.786, "regional_5r_2plus": False}},  # 1 bouts, 0.4 min, KD 1/0, dec 0, finW 1/1, finL 0/0, subL 0  THIN
    "Islam Dulatov": {"kd_per15": 4.41, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 28.3, "gender": "M", "ufc_fights": 2, "sub_loss_rate": 0.2, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 11, "pre_wins": 10, "pre_losses": 1, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 1.0, "regional_5r_2plus": False}},  # 2 bouts, 6.8 min, KD 2/0, dec 0, finW 2/2, finL 0/0, subL 0  THIN
    "Mairon Santos": {"kd_per15": 0.64, "kd_abs_per15": 0.00, "career_dec_rate": 0.500, "finish_rate": 0.500, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 26.5, "gender": "M", "ufc_fights": 4, "sub_loss_rate": 0.25, "sub_att_per15": 0.0},  # 4 bouts, 46.9 min, KD 2/0, dec 2, finW 2/4, finL 0/0, subL 0
    "Akbar Abdullaev": {"kd_per15": 50.00, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 29.2, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.25, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 13, "pre_wins": 13, "pre_losses": 0, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 1.0, "regional_5r_2plus": False}},  # 1 bouts, 0.3 min, KD 1/0, dec 0, finW 1/1, finL 0/0, subL 0  THIN
    "Magomed Tuchalov": {"kd_per15": 0.00, "kd_abs_per15": 0.00, "career_dec_rate": 1.000, "finish_rate": 0.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 26.9, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.25, "sub_att_per15": 1.0,
        "pre_ufc": {"pre_bouts": 6, "pre_wins": 6, "pre_losses": 0, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 1.0, "regional_5r_2plus": False}},  # 1 bouts, 15.0 min, KD 0/0, dec 1, finW 0/1, finL 0/0, subL 0  THIN
    "Ion Cutelaba": {"kd_per15": 0.18, "kd_abs_per15": 0.27, "career_dec_rate": 0.333, "finish_rate": 0.667, "been_finished_rate": 0.727, "off_ko_loss": True, "age": 33.0, "gender": "M", "ufc_fights": 21, "sub_loss_rate": 0.333, "sub_att_per15": 0.3},  # 21 bouts, 168.0 min, KD 2/3, dec 7, finW 6/9, finL 8/11, subL 4
    "Bruno Silva": {"kd_per15": 0.85, "kd_abs_per15": 0.85, "career_dec_rate": 0.250, "finish_rate": 1.000, "been_finished_rate": 0.500, "off_ko_loss": False, "age": 36.7, "gender": "M", "ufc_fights": 12, "sub_loss_rate": 0.2, "sub_att_per15": 0.2},  # 12 bouts, 123.7 min, KD 7/7, dec 3, finW 5/5, finL 3/6, subL 1
    "Jafel Filho": {"kd_per15": 0.22, "kd_abs_per15": 0.22, "career_dec_rate": 0.286, "finish_rate": 1.000, "been_finished_rate": 0.333, "off_ko_loss": False, "age": 33.6, "gender": "M", "ufc_fights": 7, "sub_loss_rate": 0.286, "sub_att_per15": 1.8},  # 7 bouts, 68.6 min, KD 1/1, dec 2, finW 4/4, finL 1/3, subL 1
    "Uran Satybaldiev": {"kd_per15": 0.84, "kd_abs_per15": 0.00, "career_dec_rate": 0.500, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 32.3, "gender": "M", "ufc_fights": 2, "sub_loss_rate": 0.2, "sub_att_per15": 1.7,
        "pre_ufc": {"pre_bouts": 8, "pre_wins": 8, "pre_losses": 0, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 0.75, "regional_5r_2plus": True}},  # 2 bouts, 17.8 min, KD 1/0, dec 1, finW 1/1, finL 0/1, subL 0  THIN
    "Ivan Gnizditskiy": {"off_ko_loss": False, "age": 30.6, "gender": "M", "ufc_fights": 0, "sub_loss_rate": 0.25,
        "pre_ufc": {"pre_bouts": 5, "pre_wins": 5, "pre_losses": 0, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 1.0, "regional_5r_2plus": False}},  # UFC DEBUT: rate keys and finish_rate left out (division-mean fallback)
    "Marco Tulio": {"kd_per15": 1.31, "kd_abs_per15": 1.05, "career_dec_rate": 0.333, "finish_rate": 0.750, "been_finished_rate": 0.500, "off_ko_loss": False, "age": 32.5, "gender": "M", "ufc_fights": 6, "sub_loss_rate": 0.167, "sub_att_per15": 0.3},  # 6 bouts, 57.3 min, KD 5/4, dec 2, finW 3/4, finL 1/2, subL 0
    "JunYong Park": {"kd_per15": 0.09, "kd_abs_per15": 0.00, "career_dec_rate": 0.615, "finish_rate": 0.333, "been_finished_rate": 0.500, "off_ko_loss": False, "age": 35.8, "gender": "M", "ufc_fights": 13, "sub_loss_rate": 0.25, "sub_att_per15": 0.8},  # 13 bouts, 159.8 min, KD 1/0, dec 8, finW 3/9, finL 2/4, subL 1
    "Pavel Andrusca": {"kd_per15": 0.00, "kd_abs_per15": 1.00, "career_dec_rate": 1.000, "finish_rate": 0.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 24.6, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.25, "sub_att_per15": 1.0,
        "pre_ufc": {"pre_bouts": 8, "pre_wins": 8, "pre_losses": 0, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 0.875, "regional_5r_2plus": False}},  # 1 bouts, 15.0 min, KD 0/1, dec 1, finW 0/1, finL 0/0, subL 0  THIN
    "Mahammadali Osmanli": {"kd_per15": 0.00, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 22.3, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.333, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 12, "pre_wins": 11, "pre_losses": 1, "pre_ko_losses": 0, "pre_sub_losses": 1, "pre_finish_rate": 0.818, "regional_5r_2plus": False}},  # 1 bouts, 2.3 min, KD 0/0, dec 0, finW 0/0, finL 0/1, subL 0  THIN
    "Modestino Rodrigues": {"kd_per15": 50.00, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 23.2, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.2, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 8, "pre_wins": 7, "pre_losses": 1, "pre_ko_losses": 1, "pre_sub_losses": 0, "pre_finish_rate": 1.0, "regional_5r_2plus": False}},  # 1 bouts, 0.3 min, KD 1/0, dec 0, finW 1/1, finL 0/0, subL 0  THIN
    "Matthieu Duclos": {"kd_per15": 1.23, "kd_abs_per15": 2.46, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 1.000, "off_ko_loss": False, "age": 31.7, "gender": "M", "ufc_fights": 2, "sub_loss_rate": 0.286, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 12, "pre_wins": 10, "pre_losses": 2, "pre_ko_losses": 1, "pre_sub_losses": 1, "pre_finish_rate": 0.8, "regional_5r_2plus": False}},  # 2 bouts, 12.2 min, KD 1/2, dec 0, finW 1/1, finL 1/1, subL 0  THIN
    "Abdul Hussein": {"kd_per15": 1.15, "kd_abs_per15": 0.00, "career_dec_rate": 0.000, "finish_rate": 1.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 29.3, "gender": "M", "ufc_fights": 1, "sub_loss_rate": 0.333, "sub_att_per15": 3.0,
        "pre_ufc": {"pre_bouts": 17, "pre_wins": 15, "pre_losses": 2, "pre_ko_losses": 0, "pre_sub_losses": 1, "pre_finish_rate": 0.933, "regional_5r_2plus": False}},  # 1 bouts, 13.1 min, KD 1/0, dec 0, finW 1/1, finL 0/0, subL 0  THIN
    "Hecher Sosa": {"kd_per15": 0.00, "kd_abs_per15": 0.00, "career_dec_rate": 1.000, "finish_rate": 0.000, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 31.3, "gender": "M", "ufc_fights": 2, "sub_loss_rate": 0.2, "sub_att_per15": 1.0,
        "pre_ufc": {"pre_bouts": 13, "pre_wins": 12, "pre_losses": 1, "pre_ko_losses": 1, "pre_sub_losses": 0, "pre_finish_rate": 0.667, "regional_5r_2plus": False}},  # 2 bouts, 30.0 min, KD 0/0, dec 2, finW 0/2, finL 0/0, subL 0  THIN
    "Luke Riley": {"kd_per15": 1.27, "kd_abs_per15": 0.00, "career_dec_rate": 0.333, "finish_rate": 0.667, "been_finished_rate": 0.000, "off_ko_loss": False, "age": 27.4, "gender": "M", "ufc_fights": 3, "sub_loss_rate": 0.25, "sub_att_per15": 0.0,
        "pre_ufc": {"pre_bouts": 11, "pre_wins": 11, "pre_losses": 0, "pre_ko_losses": 0, "pre_sub_losses": 0, "pre_finish_rate": 0.727, "regional_5r_2plus": False}},  # 3 bouts, 23.6 min, KD 2/0, dec 1, finW 2/3, finL 0/0, subL 0  THIN
    "Gabriel Santos": {"kd_per15": 0.29, "kd_abs_per15": 0.58, "career_dec_rate": 0.500, "finish_rate": 0.500, "been_finished_rate": 0.500, "off_ko_loss": False, "age": 30.0, "gender": "M", "ufc_fights": 4, "sub_loss_rate": 0.167, "sub_att_per15": 1.2},  # 4 bouts, 51.3 min, KD 1/2, dec 2, finW 1/2, finL 1/2, subL 0
    "Mateusz Rebecki": {"kd_per15": 0.69, "kd_abs_per15": 0.00, "career_dec_rate": 0.400, "finish_rate": 0.667, "been_finished_rate": 0.500, "off_ko_loss": False, "age": 34.2, "gender": "M", "ufc_fights": 10, "sub_loss_rate": 0.25, "sub_att_per15": 0.4},  # 10 bouts, 108.0 min, KD 5/0, dec 4, finW 4/6, finL 2/4, subL 1
    "Elves Brener": {"kd_per15": 0.56, "kd_abs_per15": 0.37, "career_dec_rate": 0.429, "finish_rate": 0.750, "been_finished_rate": 0.333, "off_ko_loss": False, "age": 29.2, "gender": "M", "ufc_fights": 7, "sub_loss_rate": 0.143, "sub_att_per15": 0.0},  # 7 bouts, 80.1 min, KD 3/2, dec 3, finW 3/4, finL 1/3, subL 0
}

market_odds = {
    # PENDING Tue/Wed: 4-book median moneylines (FanDuel, Caesars, BetRivers, Unibet)
}

career_context = {
    "Israel Adesanya": {"momentum": 0.0, "career_ko_pct": 16/24, "career_sub_pct": 0/24, "career_wins": 24},  # PENDING momentum from BFO L5 (Tue/Wed); record 24-6-0
    "Shara Magomedov": {"momentum": 0.0, "career_ko_pct": 12/17, "career_sub_pct": 0/17, "career_wins": 17},  # PENDING momentum from BFO L5 (Tue/Wed); record 17-1-0
    "Ian Machado Garry": {"momentum": 0.0, "career_ko_pct": 7/17, "career_sub_pct": 1/17, "career_wins": 17},  # PENDING momentum from BFO L5 (Tue/Wed); record 17-2-0
    "Yaroslav Amosov": {"momentum": 0.0, "career_ko_pct": 9/30, "career_sub_pct": 13/30, "career_wins": 30},  # PENDING momentum from BFO L5 (Tue/Wed); record 30-1-0
    "Serghei Spivac": {"momentum": 0.0, "career_ko_pct": 7/18, "career_sub_pct": 8/18, "career_wins": 18},  # PENDING momentum from BFO L5 (Tue/Wed); record 18-7-0
    "Mario Pinto": {"momentum": 0.0, "career_ko_pct": 8/13, "career_sub_pct": 1/13, "career_wins": 13},  # PENDING momentum from BFO L5 (Tue/Wed); record 13-0-0
    "Levan Chokheli": {"momentum": 0.0, "career_ko_pct": 12/15, "career_sub_pct": 0/15, "career_wins": 15},  # PENDING momentum from BFO L5 (Tue/Wed); record 15-3-0 (1 NC)
    "Islam Dulatov": {"momentum": 0.0, "career_ko_pct": 7/12, "career_sub_pct": 5/12, "career_wins": 12},  # PENDING momentum from BFO L5 (Tue/Wed); record 12-1-0
    "Mairon Santos": {"momentum": 0.0, "career_ko_pct": 9/17, "career_sub_pct": 0/17, "career_wins": 17},  # PENDING momentum from BFO L5 (Tue/Wed); record 18-1-0
    "Akbar Abdullaev": {"momentum": 0.0, "career_ko_pct": 13/14, "career_sub_pct": 1/14, "career_wins": 14},  # PENDING momentum from BFO L5 (Tue/Wed); record 14-0-0
    "Magomed Tuchalov": {"momentum": 0.0, "career_ko_pct": 5/7, "career_sub_pct": 1/7, "career_wins": 7},  # PENDING momentum from BFO L5 (Tue/Wed); record 7-0-0
    "Ion Cutelaba": {"momentum": 0.0, "career_ko_pct": 13/20, "career_sub_pct": 4/20, "career_wins": 20},  # PENDING momentum from BFO L5 (Tue/Wed); record 20-12-1 (1 NC)
    "Bruno Silva": {"momentum": 0.0, "career_ko_pct": 6/15, "career_sub_pct": 5/15, "career_wins": 15},  # PENDING momentum from BFO L5 (Tue/Wed); record 15-9-2 (1 NC)
    "Jafel Filho": {"momentum": 0.0, "career_ko_pct": 5/17, "career_sub_pct": 11/17, "career_wins": 17},  # PENDING momentum from BFO L5 (Tue/Wed); record 17-5-0
    "Uran Satybaldiev": {"momentum": 0.0, "career_ko_pct": 5/9, "career_sub_pct": 2/9, "career_wins": 9},  # PENDING momentum from BFO L5 (Tue/Wed); record 9-1-0
    "Ivan Gnizditskiy": {"momentum": 0.0, "career_ko_pct": 4/5, "career_sub_pct": 1/5, "career_wins": 5},  # PENDING momentum from BFO L5 (Tue/Wed); record 5-0-0
    "Marco Tulio": {"momentum": 0.0, "career_ko_pct": 10/14, "career_sub_pct": 1/14, "career_wins": 14},  # PENDING momentum from BFO L5 (Tue/Wed); record 14-3-0
    "JunYong Park": {"momentum": 0.0, "career_ko_pct": 5/19, "career_sub_pct": 6/19, "career_wins": 19},  # PENDING momentum from BFO L5 (Tue/Wed); record 19-7-0
    "Pavel Andrusca": {"momentum": 0.0, "career_ko_pct": 6/9, "career_sub_pct": 1/9, "career_wins": 9},  # PENDING momentum from BFO L5 (Tue/Wed); record 9-0-0
    "Mahammadali Osmanli": {"momentum": 0.0, "career_ko_pct": 3/11, "career_sub_pct": 6/11, "career_wins": 11},  # PENDING momentum from BFO L5 (Tue/Wed); record 13-2-0
    "Modestino Rodrigues": {"momentum": 0.0, "career_ko_pct": 8/8, "career_sub_pct": 0/8, "career_wins": 8},  # PENDING momentum from BFO L5 (Tue/Wed); record 8-1-0
    "Matthieu Duclos": {"momentum": 0.0, "career_ko_pct": 9/11, "career_sub_pct": 0/11, "career_wins": 11},  # PENDING momentum from BFO L5 (Tue/Wed); record 11-3-0
    "Abdul Hussein": {"momentum": 0.0, "career_ko_pct": 5/16, "career_sub_pct": 10/16, "career_wins": 16},  # PENDING momentum from BFO L5 (Tue/Wed); record 16-2-0
    "Hecher Sosa": {"momentum": 0.0, "career_ko_pct": 6/14, "career_sub_pct": 2/14, "career_wins": 14},  # PENDING momentum from BFO L5 (Tue/Wed); record 15-1-0
    "Luke Riley": {"momentum": 0.0, "career_ko_pct": 10/14, "career_sub_pct": 0/14, "career_wins": 14},  # PENDING momentum from BFO L5 (Tue/Wed); record 14-0-0
    "Gabriel Santos": {"momentum": 0.0, "career_ko_pct": 3/12, "career_sub_pct": 5/12, "career_wins": 12},  # PENDING momentum from BFO L5 (Tue/Wed); record 12-2-0
    "Mateusz Rebecki": {"momentum": 0.0, "career_ko_pct": 10/21, "career_sub_pct": 7/21, "career_wins": 21},  # PENDING momentum from BFO L5 (Tue/Wed); record 21-5-0
    "Elves Brener": {"momentum": 0.0, "career_ko_pct": 4/17, "career_sub_pct": 11/17, "career_wins": 17},  # PENDING momentum from BFO L5 (Tue/Wed); record 17-6-0
}
