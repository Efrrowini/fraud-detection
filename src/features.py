import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Time-based features
    df['Hour']         = (df['Time'] % 86400) // 3600
    df['IsNight']      = ((df['Hour'] >= 22) | (df['Hour'] <= 5)).astype(int)
    df['DayOfWeek']    = (df['Time'] // 86400) % 7

    # Amount features
    df['LogAmount']    = np.log1p(df['Amount'])
    df['AmountBin']    = pd.cut(df['Amount'],
        bins=[-0.01, 10, 50, 200, 1000, np.inf],
        labels=[0, 1, 2, 3, 4]).astype(int)
    df['IsRoundAmount'] = (df['Amount'] % 10 == 0).astype(int)

    # Drop raw Time and Amount
    df = df.drop(columns=['Time', 'Amount'])
    return df


def build_and_split(
    raw_path: str = 'data/raw/creditcard.csv',
    out_dir:  str = 'data/processed',
    apply_smote: bool = True
):
    print('Loading data...')
    df = pd.read_csv(raw_path)
    df = engineer_features(df)

    X = df.drop(columns=['Class'])
    y = df['Class']

    # Stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    # Scale amount features
    scaler = StandardScaler()
    cols_to_scale = ['LogAmount', 'Hour']
    X_train[cols_to_scale] = scaler.fit_transform(X_train[cols_to_scale])
    X_test[cols_to_scale]  = scaler.transform(X_test[cols_to_scale])

    # SMOTE on training set only
    if apply_smote:
        print('Applying SMOTE...')
        sm = SMOTE(random_state=42, sampling_strategy=0.1)
        X_train, y_train = sm.fit_resample(X_train, y_train)
        print(f'After SMOTE — fraud: {y_train.sum():,} / total: {len(y_train):,}')

    # Save
    pd.concat([X_train, y_train], axis=1).to_csv(
        f'{out_dir}/train.csv', index=False)
    pd.concat([X_test, y_test], axis=1).to_csv(
        f'{out_dir}/test.csv', index=False)

    print(f'Train: {len(X_train):,} | Test: {len(X_test):,}')
    return X_train, X_test, y_train, y_test


if __name__ == '__main__':
    build_and_split()